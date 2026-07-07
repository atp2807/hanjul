"""doc 리포지토리 포트(Protocol) — 도메인이 요구하는 영속성 계약.

구현체: infrastructure.doc_repo.SqlDocumentRepository/SqlShareRepository (운영) /
tests 의 FakeDocumentRepo·FakeShareRepo (Fake). 서비스는 이 Protocol 에만
의존한다(SQLAlchemy·SQL·_cd/_ts 컬럼 지식은 구현체에만).
"""
from typing import Protocol
from uuid import UUID

from src.features.doc.domain.models import Document, ShareLink


class DocumentRepository(Protocol):
    async def get(self, doc_id: UUID) -> Document | None:
        """soft delete 제외. 없으면 None."""
        ...

    async def list(
        self, page: int, page_size: int, *, viewer_id: UUID | None = None
    ) -> tuple[list[Document], int]:
        """(items, total) — soft delete 제외.

        가시성: ownerless(owner_id NULL) + viewer 소유분. viewer_id 가 None(비로그인)
        이면 ownerless 만. total 은 이 가시성 필터를 반영한 개수. 최신순(created_at DESC).
        """
        ...

    async def create(self, document: Document) -> Document:
        ...

    async def update_html(self, doc_id: UUID, html: str) -> Document | None:
        """soft delete 아닌 문서만 갱신. 대상 없으면 None."""
        ...

    async def soft_delete(self, doc_id: UUID) -> bool:
        """삭제 성공 시 True, 대상 없음/이미 삭제 시 False."""
        ...


class ShareRepository(Protocol):
    """공유 링크 저장소 계약.

    회수 의미론: get_by_token 은 회수분도 그대로 반환한다 — 404 판정(회수/부재 동일)은
    service 몫이라 저장소는 정보를 숨기지 않는다. 공개 접근마다 실조회가 정본.
    """

    async def create(self, share: ShareLink) -> ShareLink:
        ...

    async def get_by_token(self, token: str) -> ShareLink | None:
        """토큰으로 조회. 회수분 포함(있는 그대로)."""
        ...

    async def get_by_id(self, share_id: UUID) -> ShareLink | None:
        ...

    async def list_by_document(
        self, document_id: UUID, page: int, page_size: int
    ) -> tuple[list[ShareLink], int]:
        """(items, total) — 회수분 포함 전체(발급자가 회수 상태를 봐야 하므로). 최신순."""
        ...

    async def revoke(self, share_id: UUID) -> None:
        """멱등 회수 — 이미 회수됐거나 없으면 무시. revoked_ts 를 최초 1회만 찍는다."""
        ...
