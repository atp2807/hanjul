"""인메모리 DocumentRepository/ShareRepository — DB 없이 서비스 테스트.

도메인 Protocol 을 구조적으로 만족한다(Protocol 이라 상속 불필요). juldoc InMemory repo
이식 — id 는 UUID(hanjul 규약), soft delete·ownerless 가시성·멱등 회수 의미 동일.
"""
from datetime import UTC, datetime
from uuid import UUID

from src.features.doc.domain.models import Document, ShareLink


def _now() -> datetime:
    return datetime.now(UTC)


class FakeDocumentRepo:
    def __init__(self) -> None:
        self._store: dict[UUID, Document] = {}

    async def get(self, doc_id: UUID) -> Document | None:
        doc = self._store.get(doc_id)
        if doc is None or doc.deleted_at is not None:
            return None
        return doc

    async def list(
        self, page: int, page_size: int, *, viewer_id: UUID | None = None
    ) -> tuple[list[Document], int]:
        alive = [
            d
            for d in self._store.values()
            if d.deleted_at is None and (d.owner_id is None or d.owner_id == viewer_id)
        ]
        alive.sort(key=lambda d: d.created_at, reverse=True)
        total = len(alive)
        start = (page - 1) * page_size
        return alive[start : start + page_size], total

    async def create(self, document: Document) -> Document:
        self._store[document.id] = document
        return document

    async def update_html(self, doc_id: UUID, html: str) -> Document | None:
        doc = self._store.get(doc_id)
        if doc is None or doc.deleted_at is not None:
            return None
        doc.html = html
        doc.updated_at = _now()
        return doc

    async def soft_delete(self, doc_id: UUID) -> bool:
        doc = self._store.get(doc_id)
        if doc is None or doc.deleted_at is not None:
            return False
        doc.deleted_at = _now()
        return True


class FakeShareRepo:
    def __init__(self) -> None:
        self._store: dict[UUID, ShareLink] = {}
        self._by_token: dict[str, UUID] = {}

    async def create(self, share: ShareLink) -> ShareLink:
        self._store[share.id] = share
        self._by_token[share.token] = share.id
        return share

    async def get_by_token(self, token: str) -> ShareLink | None:
        share_id = self._by_token.get(token)
        return self._store.get(share_id) if share_id else None

    async def get_by_id(self, share_id: UUID) -> ShareLink | None:
        return self._store.get(share_id)

    async def list_by_document(
        self, document_id: UUID, page: int, page_size: int
    ) -> tuple[list[ShareLink], int]:
        rows = [s for s in self._store.values() if s.document_id == document_id]
        rows.sort(key=lambda s: s.created_at, reverse=True)
        total = len(rows)
        start = (page - 1) * page_size
        return rows[start : start + page_size], total

    async def revoke(self, share_id: UUID) -> None:
        share = self._store.get(share_id)
        if share is None or share.revoked_at is not None:
            return  # 부재/이미 회수 → no-op (멱등)
        share.revoked_at = _now()
