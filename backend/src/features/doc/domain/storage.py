"""미디어 오브젝트 저장 포트(Protocol) — content-addressed key(sha256+확장자)를 다룬다.

구현체: infrastructure.storage_r2.R2Storage(Cloudflare R2) / storage_local.LocalStorage(폴백).
DI(dependencies)는 R2 설정 유무로 둘 중 하나를 조립한다("자격증명 나중 주입" 컨벤션 —
DATABASE_URL 폴백과 동일 패턴). document_service(수출 이미지 resolve)와 media_service 가
같은 어댑터 인스턴스를 공유한다(업로드↔수출 일관).

put/get/exists 는 코루틴 — R2 구현이 동기 boto3 를 run_in_executor 로 감싸 이벤트 루프를
블로킹하지 않는다. url_for 는 순수 문자열 조립이라 동기.
"""
from typing import Protocol, runtime_checkable


@runtime_checkable
class StorageAdapter(Protocol):
    async def put(self, key: str, data: bytes, content_type: str) -> None:
        """오브젝트 저장. 같은 key(=같은 바이트) 재업로드는 멱등(덮어쓰기)."""
        ...

    async def get(self, key: str) -> bytes | None:
        """오브젝트 바이트. 없으면 None (폴백 서버 프록시 서빙용)."""
        ...

    def url_for(self, key: str) -> str:
        """서빙 URL. R2 는 절대 URL(공개/내부), 로컬은 상대 '/media/{key}'.

        엔드포인트는 '://' 포함 여부로 리다이렉트(R2)/프록시(로컬)를 가른다.
        """
        ...

    async def exists(self, key: str) -> bool:
        """오브젝트 존재 여부."""
        ...
