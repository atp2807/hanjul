"""cover 통합 — 실 DB(SQLite)에서 표지 URL 영속."""
from sqlalchemy import select

from src.features.books.infrastructure.book_repo import SqlBookRepository
from src.features.cover.application.cover_service import CoverService
from src.features.cover.infrastructure.cover_repo import SqlCoverRepository
from src.infrastructure.db.models.book import Book
from tests.fixtures.fake_cover import FakeCoverGenerator


async def test_generated_cover_persists_on_book(sessionmaker):
    async with sessionmaker() as s:
        book_id = await SqlBookRepository(s).create_book(title="책", kind="BOOK", language="ko")

    async with sessionmaker() as s:
        svc = CoverService(SqlCoverRepository(s), FakeCoverGenerator("https://img/c.png"))
        url = await svc.generate_for_book(book_id, "표지 프롬프트")
        assert url == "https://img/c.png"

    async with sessionmaker() as s2:
        book = (await s2.execute(select(Book).where(Book.id == book_id))).scalar_one()
        assert book.cover_url == "https://img/c.png"
