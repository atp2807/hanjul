"""catalog 통합 — 실 DB(SQLite)에서 출판 → 스토어 노출."""
from src.features.books.infrastructure.book_repo import SqlBookRepository
from src.features.catalog.application.catalog_service import CatalogService
from src.features.catalog.domain.models import PUBLISHED
from src.features.catalog.infrastructure.catalog_repo import SqlCatalogRepository


async def _make_book(sessionmaker, title="한글책"):
    async with sessionmaker() as s:
        return await SqlBookRepository(s).create_book(title=title, kind="BOOK", language="ko")


async def test_publish_flow_lists_in_store(sessionmaker):
    book_id = await _make_book(sessionmaker, "베스트셀러")

    async with sessionmaker() as s:
        svc = CatalogService(SqlCatalogRepository(s))
        await svc.set_price(book_id, 9900)
        await svc.submit_for_review(book_id)
        await svc.publish(book_id)

    async with sessionmaker() as s2:
        svc = CatalogService(SqlCatalogRepository(s2))
        detail = await svc.get_store_detail(book_id)
        assert detail.status == PUBLISHED
        assert detail.price_amt == 9900

        listed = await svc.list_store(q="베스트", limit=10, offset=0)
        assert any(b.id == book_id for b in listed)


async def test_list_store_filters_by_kind(sessionmaker):
    async with sessionmaker() as s:
        book_id = await SqlBookRepository(s).create_book(title="일반책", kind="BOOK", language="ko")
        novel_id = await SqlBookRepository(s).create_book(title="웹소설책", kind="WEBNOVEL", language="ko")
        svc = CatalogService(SqlCatalogRepository(s))
        for bid in (book_id, novel_id):
            await svc.set_price(bid, 1000)
            await svc.submit_for_review(bid)
            await svc.publish(bid)

    async with sessionmaker() as s2:
        svc = CatalogService(SqlCatalogRepository(s2))
        books = await svc.list_store(kind="BOOK")
        novels = await svc.list_store(kind="WEBNOVEL")
        assert all(b.kind == "BOOK" for b in books) and any(b.id == book_id for b in books)
        assert all(b.kind == "WEBNOVEL" for b in novels) and any(b.id == novel_id for b in novels)


async def test_unpublished_not_in_store(sessionmaker):
    book_id = await _make_book(sessionmaker, "초안책")
    async with sessionmaker() as s:
        svc = CatalogService(SqlCatalogRepository(s))
        listed = await svc.list_store(q=None, limit=10, offset=0)
        assert all(b.id != book_id for b in listed)
