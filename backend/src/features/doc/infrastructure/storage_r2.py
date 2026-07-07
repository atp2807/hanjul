"""Cloudflare R2(S3 호환) 저장 어댑터 — 서버 프록시 put_object 업로드. (juldoc storage/r2 이식)

  - client lazy 생성(첫 호출 시), Config s3v4 + 명시적 타임아웃.
  - 동기 boto3 호출을 run_in_executor 로 감싸 이벤트 루프 논블로킹.
  - key 는 content-addressed(sha256+ext), 절대 URL 은 저장 X — url_for 로 서빙 시점 조립.

juldoc 대비: 오브젝트 prefix 를 'juldoc/media' → 'hanjul/media' 로 변경(버킷 공유 시 격리).
"""
import asyncio
import logging

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from src.features.doc.domain.storage import StorageAdapter

logger = logging.getLogger("storage.r2")

# hanjul 전용 오브젝트 prefix. 버킷을 공유하더라도 hanjul/media/ 아래로 격리한다.
_PREFIX = "hanjul/media"

# "부재"에 해당하는 S3/R2 에러코드 — 조용히 None/False. (head_object 는 404 로 옴.)
_MISSING_CODES = frozenset({"NoSuchKey", "NotFound", "404"})


def _err_code(e: ClientError) -> str:
    """ClientError 에서 S3 에러코드 추출(없으면 빈 문자열)."""
    return e.response.get("Error", {}).get("Code", "")


class R2Storage(StorageAdapter):
    def __init__(
        self,
        *,
        endpoint_url: str,
        access_key_id: str | None,
        secret_access_key: str | None,
        bucket_name: str,
        public_url: str = "",
    ) -> None:
        self._endpoint_url = endpoint_url
        self._access_key_id = access_key_id
        self._secret_access_key = secret_access_key
        self._bucket = bucket_name
        self._public_url = (public_url or "").rstrip("/")
        self._client = None

    @property
    def _s3(self):
        """Lazy 클라이언트. connect/read 타임아웃 명시 — 네트워크 stall 시 워커 무한 대기 방지."""
        if self._client is None:
            self._client = boto3.client(
                "s3",
                endpoint_url=self._endpoint_url,
                aws_access_key_id=self._access_key_id,
                aws_secret_access_key=self._secret_access_key,
                config=Config(
                    signature_version="s3v4",
                    connect_timeout=10,
                    read_timeout=30,
                    retries={"max_attempts": 3, "mode": "standard"},
                ),
                region_name="auto",
            )
        return self._client

    def _full_key(self, key: str) -> str:
        return f"{_PREFIX}/{key}"

    async def put(self, key: str, data: bytes, content_type: str) -> None:
        loop = asyncio.get_running_loop()
        full = self._full_key(key)

        def _put() -> None:
            try:
                self._s3.put_object(
                    Bucket=self._bucket, Key=full, Body=data, ContentType=content_type
                )
            except ClientError as e:
                # 조용한 실패 금지 — 로깅 후 재raise (업로드 실패는 호출자가 알아야 함).
                logger.error("R2 put_object 실패 key=%s code=%s", full, _err_code(e))
                raise

        await loop.run_in_executor(None, _put)

    async def get(self, key: str) -> bytes | None:
        loop = asyncio.get_running_loop()
        full = self._full_key(key)

        def _get() -> bytes | None:
            try:
                resp = self._s3.get_object(Bucket=self._bucket, Key=full)
                return resp["Body"].read()
            except ClientError as e:
                code = _err_code(e)
                if code not in _MISSING_CODES:
                    # NoSuchKey(404 상당)만 조용히 None. 그 외(AccessDenied/NoSuchBucket/
                    # SignatureDoesNotMatch 등 오설정)는 진단 가능하게 로깅한다.
                    logger.warning("R2 get_object 실패 key=%s code=%s", full, code)
                return None

        return await loop.run_in_executor(None, _get)

    async def exists(self, key: str) -> bool:
        loop = asyncio.get_running_loop()
        full = self._full_key(key)

        def _head() -> bool:
            try:
                self._s3.head_object(Bucket=self._bucket, Key=full)
                return True
            except ClientError as e:
                code = _err_code(e)
                if code not in _MISSING_CODES:
                    logger.warning("R2 head_object 실패 key=%s code=%s", full, code)
                return False

        return await loop.run_in_executor(None, _head)

    def url_for(self, key: str) -> str:
        """R2 공개 URL(설정 시) 또는 내부 엔드포인트 URL. 항상 절대 URL."""
        full = self._full_key(key)
        if self._public_url:
            return f"{self._public_url}/{full}"
        return f"{self._endpoint_url.rstrip('/')}/{self._bucket}/{full}"
