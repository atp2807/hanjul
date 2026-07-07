"""doc 표현 레이어 DI 합성 루트 (books 패턴).

storage 는 프로세스 1개를 공유한다(lru_cache) — document_service(수출 이미지 resolve)와
media_service(업로드)가 같은 어댑터 인스턴스를 봐야 업로드↔수출이 일관된다. R2 설정 유무로
R2Storage/LocalStorage 를 조립한다(DATABASE_URL 폴백과 동일한 "자격증명 나중 주입" 패턴).
"""
import logging
from functools import lru_cache
from pathlib import Path

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import get_session
from src.config.settings import Settings, settings
from src.features.doc.application.document_service import DocumentService
from src.features.doc.application.media_service import MediaService
from src.features.doc.application.share_service import ShareService
from src.features.doc.domain.storage import StorageAdapter
from src.features.doc.infrastructure.doc_repo import (
    SqlDocumentRepository,
    SqlShareRepository,
)
from src.features.doc.infrastructure.storage_local import LocalStorage
from src.features.doc.infrastructure.storage_r2 import R2Storage

logger = logging.getLogger("app")


def build_storage(cfg: Settings) -> StorageAdapter:
    """미디어 저장 어댑터 선택 — DATABASE_URL 폴백과 동일 패턴.

    R2_ENDPOINT_URL + R2_BUCKET_NAME 이 둘 다 있으면 R2Storage(운영), 아니면 LocalStorage
    (개발 폴백 — MEDIA_DIR 하위). R2 클라이언트는 lazy 라 여기서 조립해도 네트워크 접속 없음.
    """
    if cfg.R2_ENDPOINT_URL and cfg.R2_BUCKET_NAME:
        if not (cfg.R2_ACCESS_KEY_ID and cfg.R2_SECRET_ACCESS_KEY):
            # 부분설정 경고: 엔드포인트·버킷은 있는데 키가 없으면 업로드가 인증 에러로 실패.
            # fail-fast 아님(개발 중 키 누락 방치 가능) — 경고만 남기고 R2 를 선택한다.
            logger.warning(
                "R2 partially configured — endpoint/bucket set but access key/secret "
                "missing; uploads will fail with auth errors."
            )
        return R2Storage(
            endpoint_url=cfg.R2_ENDPOINT_URL,
            access_key_id=cfg.R2_ACCESS_KEY_ID or None,
            secret_access_key=cfg.R2_SECRET_ACCESS_KEY or None,
            bucket_name=cfg.R2_BUCKET_NAME,
            public_url=cfg.R2_PUBLIC_URL or "",
        )
    return LocalStorage(Path(cfg.MEDIA_DIR))


@lru_cache
def _storage() -> StorageAdapter:
    """프로세스 공유 storage 싱글턴(업로드↔수출 일관). 최초 호출 시 조립."""
    return build_storage(settings)


def get_document_service(session: AsyncSession = Depends(get_session)) -> DocumentService:
    return DocumentService(SqlDocumentRepository(session), _storage())


def get_share_service(session: AsyncSession = Depends(get_session)) -> ShareService:
    # ShareService 는 같은 세션의 DocumentService 를 재사용(정본 HTML·정화 왕복 단일 경로).
    documents = DocumentService(SqlDocumentRepository(session), _storage())
    return ShareService(SqlShareRepository(session), documents)


def get_media_service() -> MediaService:
    return MediaService(_storage())
