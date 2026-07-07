"""DocumentRepository/ShareRepository 의 SQLAlchemy async 구현. (juldoc asyncpg repo 재작성)

juldoc PgDocumentRepo/PgShareRepo 의 raw SQL 을 SQLAlchemy 2.0 async 로 옮긴 것.
쿼리 의미(soft delete 필터·ownerless OR owner 가시성·최신순·토큰 조회·멱등 회수)를
그대로 보존한다. SqlBookRepository 스타일(add/flush/commit).

이름 충돌 회피: ORM 모델은 DocumentRow/ShareLinkRow 로 별칭, 도메인 값객체는 Document/ShareLink.
"""
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.features.doc.domain.models import Capability, Document, ShareLink
from src.infrastructure.db.models.doc import Document as DocumentRow
from src.infrastructure.db.models.doc import ShareLink as ShareLinkRow


def _now() -> datetime:
    return datetime.now(UTC)


def _to_document(row: DocumentRow) -> Document:
    return Document(
        id=row.id,
        title=row.title,
        format=row.format,
        html=row.html,
        source_hash=row.source_hash,
        created_at=row.created_at,
        updated_at=row.updated_at,
        deleted_at=row.deleted_at,
        owner_id=row.owner_id,
    )


class SqlDocumentRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, doc_id: UUID) -> Document | None:
        stmt = select(DocumentRow).where(
            DocumentRow.id == doc_id, DocumentRow.deleted_at.is_(None)
        )
        row = (await self.session.execute(stmt)).scalar_one_or_none()
        return _to_document(row) if row else None

    async def list(
        self, page: int, page_size: int, *, viewer_id: UUID | None = None
    ) -> tuple[list[Document], int]:
        offset = (page - 1) * page_size
        # 가시성: ownerless + viewer 소유분. 비로그인(viewer_id None)은 ownerless 만.
        if viewer_id is None:
            visibility = DocumentRow.owner_id.is_(None)
        else:
            visibility = or_(
                DocumentRow.owner_id.is_(None), DocumentRow.owner_id == viewer_id
            )
        cond = and_(DocumentRow.deleted_at.is_(None), visibility)
        total = await self.session.scalar(
            select(func.count()).select_from(DocumentRow).where(cond)
        )
        rows = (
            await self.session.execute(
                select(DocumentRow)
                .where(cond)
                .order_by(DocumentRow.created_at.desc())
                .limit(page_size)
                .offset(offset)
            )
        ).scalars().all()
        return [_to_document(r) for r in rows], int(total or 0)

    async def create(self, document: Document) -> Document:
        row = DocumentRow(
            id=document.id,
            title=document.title,
            format=document.format,
            html=document.html,
            source_hash=document.source_hash,
            owner_id=document.owner_id,
            created_at=document.created_at,
            updated_at=document.updated_at,
        )
        self.session.add(row)
        await self.session.flush()
        await self.session.commit()
        return _to_document(row)

    async def update_html(self, doc_id: UUID, html: str) -> Document | None:
        row = await self.session.get(DocumentRow, doc_id)
        if row is None or row.deleted_at is not None:
            return None
        row.html = html
        row.updated_at = _now()
        await self.session.commit()
        return _to_document(row)

    async def soft_delete(self, doc_id: UUID) -> bool:
        # deleted_ts IS NULL 가드 → 멱등(이미 삭제된 대상은 영향 0행 → False).
        result = await self.session.execute(
            update(DocumentRow)
            .where(DocumentRow.id == doc_id, DocumentRow.deleted_at.is_(None))
            .values(deleted_at=_now())
        )
        await self.session.commit()
        return result.rowcount > 0


def _to_share(row: ShareLinkRow) -> ShareLink:
    return ShareLink(
        id=row.id,
        document_id=row.document_id,
        token=row.token,
        capability=Capability(row.capability),
        created_at=row.created_at,
        revoked_at=row.revoked_at,
    )


class SqlShareRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, share: ShareLink) -> ShareLink:
        row = ShareLinkRow(
            id=share.id,
            document_id=share.document_id,
            token=share.token,
            capability=str(share.capability),
            created_at=share.created_at,
            revoked_at=share.revoked_at,
        )
        self.session.add(row)
        await self.session.flush()
        await self.session.commit()
        return _to_share(row)

    async def get_by_token(self, token: str) -> ShareLink | None:
        # 회수분 포함(있는 그대로) — 404 판정(회수/부재 동일)은 service 몫.
        row = (
            await self.session.execute(
                select(ShareLinkRow).where(ShareLinkRow.token == token)
            )
        ).scalar_one_or_none()
        return _to_share(row) if row else None

    async def get_by_id(self, share_id: UUID) -> ShareLink | None:
        row = await self.session.get(ShareLinkRow, share_id)
        return _to_share(row) if row else None

    async def list_by_document(
        self, document_id: UUID, page: int, page_size: int
    ) -> tuple[list[ShareLink], int]:
        offset = (page - 1) * page_size
        total = await self.session.scalar(
            select(func.count())
            .select_from(ShareLinkRow)
            .where(ShareLinkRow.document_id == document_id)
        )
        rows = (
            await self.session.execute(
                select(ShareLinkRow)
                .where(ShareLinkRow.document_id == document_id)
                .order_by(ShareLinkRow.created_at.desc())
                .limit(page_size)
                .offset(offset)
            )
        ).scalars().all()
        return [_to_share(r) for r in rows], int(total or 0)

    async def revoke(self, share_id: UUID) -> None:
        # revoked_ts IS NULL 가드로 최초 1회만 찍는다 → 멱등 + 재활성화 불가.
        await self.session.execute(
            update(ShareLinkRow)
            .where(ShareLinkRow.id == share_id, ShareLinkRow.revoked_at.is_(None))
            .values(revoked_at=_now())
        )
        await self.session.commit()
