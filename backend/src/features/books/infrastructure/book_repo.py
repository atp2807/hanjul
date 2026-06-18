"""BookRepository 의 SQLAlchemy 구현."""
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.features.books.domain.models import BlockView, BookView, ChapterView
from src.infrastructure.db.models.book import Block, Book, Chapter


class SqlBookRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_book(self, *, title: str, kind: str, language: str) -> UUID:
        book = Book(title=title, kind=kind, language=language)
        self.session.add(book)
        await self.session.flush()
        await self.session.commit()
        return book.id

    async def book_exists(self, book_id: UUID) -> bool:
        return await self.session.get(Book, book_id) is not None

    async def add_chapter_with_blocks(
        self, book_id: UUID, title: str | None, blocks: list[dict]
    ) -> UUID:
        # 다음 장 순서 = 기존 장 개수 (0-based append)
        count = await self.session.scalar(
            select(func.count()).select_from(Chapter).where(Chapter.book_id == book_id)
        )
        chapter = Chapter(book_id=book_id, title=title, order_no=count or 0)
        self.session.add(chapter)
        await self.session.flush()
        for i, b in enumerate(blocks):
            self.session.add(
                Block(chapter_id=chapter.id, order_no=i, block_type=b["type"], html=b["html"])
            )
        await self.session.commit()
        return chapter.id

    async def get_content(self, book_id: UUID) -> BookView | None:
        stmt = (
            select(Book)
            .where(Book.id == book_id)
            .options(selectinload(Book.chapters).selectinload(Chapter.blocks))
        )
        book = (await self.session.execute(stmt)).scalar_one_or_none()
        if book is None:
            return None
        return BookView(
            id=book.id,
            title=book.title,
            kind=book.kind,
            language=book.language,
            status=book.status,
            price_amt=int(book.price_amt) if book.price_amt is not None else None,
            chapters=[
                ChapterView(
                    id=c.id,
                    title=c.title,
                    order_no=c.order_no,
                    blocks=[
                        BlockView(id=bl.id, order_no=bl.order_no, block_type=bl.block_type, html=bl.html)
                        for bl in c.blocks
                    ],
                )
                for c in book.chapters
            ],
        )
