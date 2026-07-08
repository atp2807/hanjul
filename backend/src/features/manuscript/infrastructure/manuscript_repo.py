"""manuscript SQLAlchemy 어댑터 — ms.manuscript_book / ms.manuscript_revision."""
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.features.manuscript.domain.models import MAX_REVISIONS_PER_CHAPTER, ChapterState, ManuscriptBookView
from src.infrastructure.db.models.manuscript import ManuscriptBook, ManuscriptRevision


def _book_view(b: ManuscriptBook) -> ManuscriptBookView:
    return ManuscriptBookView(
        id=b.id, account_id=b.account_id, sync_key=b.sync_key, title=b.title,
        created_at=b.created_at, updated_at=b.updated_at,
    )


class SqlManuscriptRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_book_by_sync_key(self, sync_key: UUID) -> ManuscriptBookView | None:
        row = (
            await self.session.execute(
                select(ManuscriptBook).where(ManuscriptBook.sync_key == sync_key)
            )
        ).scalar_one_or_none()
        return _book_view(row) if row else None

    async def create_book(self, account_id: UUID, sync_key: UUID, title: str) -> ManuscriptBookView:
        book = ManuscriptBook(id=uuid4(), account_id=account_id, sync_key=sync_key, title=title)
        self.session.add(book)
        await self.session.commit()
        await self.session.refresh(book)
        return _book_view(book)

    async def touch_book(self, book_id: UUID, title: str) -> None:
        book = await self.session.get(ManuscriptBook, book_id)
        if book is not None:
            book.title = title
            await self.session.commit()

    def _latest_revision_stmt(self, book_id: UUID, chapter_key: str):
        return (
            select(ManuscriptRevision)
            .where(ManuscriptRevision.book_id == book_id, ManuscriptRevision.chapter_key == chapter_key)
            .order_by(ManuscriptRevision.created_at.desc(), ManuscriptRevision.id.desc())
        )

    async def push_chapter(
        self, book_id: UUID, chapter_key: str, chapter_title: str, html: str, content_hash: str
    ) -> bool:
        latest = (
            await self.session.execute(self._latest_revision_stmt(book_id, chapter_key).limit(1))
        ).scalar_one_or_none()
        if latest is not None and latest.content_hash == content_hash:
            return False  # dedup — 직전과 동일 내용, 새 리비전 없이 스킵

        self.session.add(
            ManuscriptRevision(
                id=uuid4(), book_id=book_id, chapter_key=chapter_key,
                chapter_title=chapter_title, html=html, content_hash=content_hash,
            )
        )
        await self.session.flush()
        await self._prune(book_id, chapter_key)
        await self.session.commit()
        return True

    async def _prune(self, book_id: UUID, chapter_key: str) -> None:
        """챕터당 MAX_REVISIONS_PER_CHAPTER 초과분을 오래된 것부터 삭제."""
        rows = (
            await self.session.execute(self._latest_revision_stmt(book_id, chapter_key))
        ).scalars().all()
        for stale in rows[MAX_REVISIONS_PER_CHAPTER:]:
            await self.session.delete(stale)

    async def latest_state(self, book_id: UUID) -> list[ChapterState]:
        """챕터별 최신 리비전만 — chapter_key, created_at DESC 로 정렬해 그룹의 첫 행만 취한다
        (SQLite/Postgres 양쪽에서 동작해야 해서 DISTINCT ON/윈도함수 대신 파이썬에서 축약 —
        챕터당 리비전이 MAX_REVISIONS_PER_CHAPTER 로 상한돼 있어 book 전체를 읽어도 가볍다)."""
        rows = (
            await self.session.execute(
                select(ManuscriptRevision)
                .where(ManuscriptRevision.book_id == book_id)
                .order_by(
                    ManuscriptRevision.chapter_key,
                    ManuscriptRevision.created_at.desc(),
                    ManuscriptRevision.id.desc(),
                )
            )
        ).scalars().all()

        seen: set[str] = set()
        latest: list[ChapterState] = []
        for r in rows:
            if r.chapter_key in seen:
                continue
            seen.add(r.chapter_key)
            latest.append(
                ChapterState(
                    chapter_key=r.chapter_key, title=r.chapter_title, html=r.html,
                    content_hash=r.content_hash, updated_at=r.created_at,
                )
            )
        return latest
