"""BookService 유스케이스 테스트 (인메모리 Fake repo, DB 불필요)."""
import uuid

import pytest

from src.features.books.application.book_service import BookService
from src.features.books.domain.models import BookNotFound, NotOwner
from tests.fixtures.fake_book_repo import FakeBookRepository


@pytest.fixture
def service() -> BookService:
    return BookService(FakeBookRepository())


async def test_create_book_returns_id(service):
    book_id = await service.create_book(title="한줄 이야기")
    assert isinstance(book_id, uuid.UUID)


async def test_import_text_creates_blocks(service):
    book_id = await service.create_book(title="책")
    result = await service.import_text(book_id, "# 1장\n\n첫 문단.\n\n둘째 문단.")
    assert result.block_count == 3  # H1 + P + P
    assert isinstance(result.chapter_id, uuid.UUID)


async def test_import_into_unknown_book_raises(service):
    with pytest.raises(BookNotFound):
        await service.import_text(uuid.uuid4(), "내용")


async def test_get_content_unknown_raises(service):
    with pytest.raises(BookNotFound):
        await service.get_content(uuid.uuid4())


async def test_full_flow_content_roundtrip(service):
    book_id = await service.create_book(title="한글책", kind="WEBNOVEL", language="ko")
    await service.import_text(book_id, "# 프롤로그\n\n어느 날.", chapter_title="프롤로그")
    content = await service.get_content(book_id)

    assert content.title == "한글책"
    assert content.kind == "WEBNOVEL"
    assert len(content.chapters) == 1
    ch = content.chapters[0]
    assert ch.title == "프롤로그"
    assert [b.block_type for b in ch.blocks] == ["H1", "P"]
    assert ch.blocks[0].html == "<h1>프롤로그</h1>"


async def test_multiple_imports_append_chapters_in_order(service):
    book_id = await service.create_book(title="연재물")
    await service.import_text(book_id, "1화 내용")
    await service.import_text(book_id, "2화 내용")
    content = await service.get_content(book_id)
    assert [c.order_no for c in content.chapters] == [0, 1]


async def test_set_content_replaces_and_owner_only(service):
    author = uuid.uuid4()
    book_id = await service.create_book(title="집필책", author_id=author)
    await service.import_text(book_id, "옛 내용")  # 교체될 기존 장

    chapters = [
        {"title": "1장", "blocks": [{"type": "P", "html": "<p>새 본문</p>"}]},
        {"title": "2장", "blocks": [{"type": "P", "html": "<p>둘째</p>"}]},
    ]
    n = await service.set_content(book_id, chapters, requester_id=author)
    assert n == 2

    content = await service.get_content(book_id)
    assert [c.title for c in content.chapters] == ["1장", "2장"]  # 옛 장 사라짐
    assert content.chapters[0].blocks[0].html == "<p>새 본문</p>"


async def test_set_content_rejects_non_owner(service):
    author = uuid.uuid4()
    book_id = await service.create_book(title="내책", author_id=author)
    with pytest.raises(NotOwner):
        await service.set_content(book_id, [], requester_id=uuid.uuid4())


async def test_set_content_unknown_book_raises(service):
    with pytest.raises(BookNotFound):
        await service.set_content(uuid.uuid4(), [], requester_id=uuid.uuid4())


async def test_set_preview_limit_owner_only_and_clamped(service):
    author = uuid.uuid4()
    book_id = await service.create_book(title="책", author_id=author)
    await service.set_preview_limit(book_id, 7, requester_id=author)
    assert (await service.get_content(book_id)).preview_limit == 7

    await service.set_preview_limit(book_id, -3, requester_id=author)  # 음수 → 0
    assert (await service.get_content(book_id)).preview_limit == 0

    with pytest.raises(NotOwner):
        await service.set_preview_limit(book_id, 5, requester_id=uuid.uuid4())
