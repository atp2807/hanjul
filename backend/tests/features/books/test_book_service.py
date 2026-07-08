"""BookService 유스케이스 테스트 (인메모리 Fake repo, DB 불필요)."""
import uuid

import pytest
from src.features.books.application.book_service import BookService
from src.features.books.domain.content_rating import AgeVerificationRequired
from src.features.books.domain.models import (
    BlockView,
    BookNotFound,
    BookView,
    ChapterView,
    NotOwner,
    suggest_blurb,
    to_preview,
)

from tests.fixtures.fake_book_repo import FakeBookRepository


class _FakeAccountTier:
    """AccountTierLookup 포트의 최소 구현 — 테스트에서 계정별 인증등급을 미리 세팅."""

    def __init__(self, tiers: dict | None = None) -> None:
        self.tiers = tiers or {}

    async def get_verified_tier(self, account_id) -> str:
        return self.tiers.get(account_id, "ALL")


def test_suggest_blurb_strips_html_and_truncates():
    content = BookView(
        id=uuid.uuid4(), title="t", kind="BOOK", language="ko", status="PUBLISHED",
        chapters=[ChapterView(id=uuid.uuid4(), title="1장", order_no=0, blocks=[
            BlockView(id=uuid.uuid4(), order_no=0, block_type="H1", html="<h1>제목</h1>"),
            BlockView(id=uuid.uuid4(), order_no=1, block_type="P", html="<p>첫 <strong>문장</strong>입니다.</p>"),
        ])],
    )
    b = suggest_blurb(content)
    assert "<" not in b
    assert b == "제목 첫 문장입니다."

    long = BookView(
        id=uuid.uuid4(), title="t", kind="BOOK", language="ko", status="PUBLISHED",
        chapters=[ChapterView(id=uuid.uuid4(), title=None, order_no=0, blocks=[
            BlockView(id=uuid.uuid4(), order_no=0, block_type="P", html="<p>" + "가" * 300 + "</p>"),
        ])],
    )
    assert suggest_blurb(long).endswith("…") and len(suggest_blurb(long)) == 151


def test_to_preview_truncates_blocks_but_preserves_metadata():
    """회귀가드: 미리보기는 앞 limit개 블록만 남기되 content_rating 등 메타는 보존해야 한다.
    (과거 BookView 일부 필드만 재구성해 content_rating이 조용히 ALL로 굳던 버그.)"""
    content = BookView(
        id=uuid.uuid4(), title="t", kind="BOOK", language="ko", status="PUBLISHED",
        price_amt=5000, preview_limit=1, content_rating="AGE18",
        content_rating_detail={"violence": "AGE18"},
        chapters=[ChapterView(id=uuid.uuid4(), title="1장", order_no=0, blocks=[
            BlockView(id=uuid.uuid4(), order_no=0, block_type="P", html="<p>1</p>"),
            BlockView(id=uuid.uuid4(), order_no=1, block_type="P", html="<p>2</p>"),
        ])],
    )
    preview = to_preview(content, 1)
    # 블록은 잘렸지만
    assert sum(len(ch.blocks) for ch in preview.chapters) == 1
    # 메타는 원본 그대로 보존
    assert preview.content_rating == "AGE18"
    assert preview.content_rating_detail == {"violence": "AGE18"}
    assert preview.preview_limit == 1
    assert preview.price_amt == 5000


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


async def test_import_owner_gate(service):
    """소유자 있는 책: 본인만 import. 익명/타인 → NotOwner. 소유자 없는 책: 개방."""
    author = uuid.uuid4()
    owned = await service.create_book(title="내책", author_id=author)
    # 본인 OK
    assert (await service.import_text(owned, "본문", requester_id=author)).block_count == 1
    # 타인/익명 차단
    with pytest.raises(NotOwner):
        await service.import_text(owned, "탈취", requester_id=uuid.uuid4())
    with pytest.raises(NotOwner):
        await service.import_text(owned, "탈취")  # 익명
    # 소유자 없는 책은 익명 import 허용
    orphan = await service.create_book(title="익명책")
    assert (await service.import_text(orphan, "본문")).block_count == 1


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
    await service.import_text(book_id, "옛 내용", requester_id=author)  # 교체될 기존 장

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


# ── 연령 게이트(dc-daeb0d3d) — 본문열람 ──────────────────
async def test_get_content_no_account_tier_port_still_fails_closed():
    """account_tier 미주입(기본값) — tier가 "ALL"로 간주돼 등급있는 책은 여전히 막힌다.

    (기존 Fake 테스트 더블은 책 등급이 전부 기본값 "ALL"이라 이 fail-closed 기본값이
    실제 동작을 바꾸지 않는다 — 하위호환은 "게이트 생략"이 아니라 "안전한 기본값"으로 보장.)
    """
    repo = FakeBookRepository()
    svc = BookService(repo)
    book_id = await repo.create_book(title="AGE18책", kind="BOOK", language="ko")
    await repo.set_content_rating(book_id, "AGE18", {})

    with pytest.raises(AgeVerificationRequired):
        await svc.get_content(book_id)


async def test_get_content_no_account_tier_port_allows_all_rated_book():
    """등급 없는(기본 ALL) 책은 포트 미주입에도 기존처럼 그냥 통과 — 진짜 하위호환 지점."""
    repo = FakeBookRepository()
    svc = BookService(repo)
    book_id = await repo.create_book(title="일반책", kind="BOOK", language="ko")

    content = await svc.get_content(book_id)
    assert content.content_rating == "ALL"


async def test_get_content_blocks_unverified_account_for_restricted_book():
    repo = FakeBookRepository()
    svc = BookService(repo, account_tier=_FakeAccountTier())
    book_id = await repo.create_book(title="AGE18책", kind="BOOK", language="ko")
    await repo.set_content_rating(book_id, "AGE18", {})

    with pytest.raises(AgeVerificationRequired):
        await svc.get_content(book_id, account_id=uuid.uuid4())  # 미인증(ALL 취급) → 차단


async def test_get_content_blocks_anonymous_for_restricted_book():
    repo = FakeBookRepository()
    svc = BookService(repo, account_tier=_FakeAccountTier())
    book_id = await repo.create_book(title="AGE18책", kind="BOOK", language="ko")
    await repo.set_content_rating(book_id, "AGE18", {})

    with pytest.raises(AgeVerificationRequired):
        await svc.get_content(book_id, account_id=None)  # 비로그인 → ALL 취급 → 차단


async def test_get_content_allows_verified_reader_for_restricted_book():
    reader = uuid.uuid4()  # 책 소유자가 아닌, 인증만 받은 제3자 독자
    repo = FakeBookRepository()
    svc = BookService(repo, account_tier=_FakeAccountTier({reader: "AGE18"}))
    book_id = await repo.create_book(title="AGE18책", kind="BOOK", language="ko")
    await repo.set_content_rating(book_id, "AGE18", {})

    content = await svc.get_content(book_id, account_id=reader)
    assert content.content_rating == "AGE18"


async def test_get_content_allows_anyone_for_all_rated_book():
    repo = FakeBookRepository()
    svc = BookService(repo, account_tier=_FakeAccountTier())
    book_id = await repo.create_book(title="일반책", kind="BOOK", language="ko")

    content = await svc.get_content(book_id, account_id=None)  # 기본 등급 ALL → 누구나
    assert content.content_rating == "ALL"


async def test_get_content_owner_bypasses_gate_even_when_unverified():
    """소유 작가는 본인 등급조정으로 AGE18이 된 원고도 미인증 상태로 항상 열람 가능."""
    author = uuid.uuid4()
    repo = FakeBookRepository()
    svc = BookService(repo, account_tier=_FakeAccountTier())  # author는 어떤 tier도 세팅 안 함(ALL)
    book_id = await repo.create_book(title="내 원고", kind="BOOK", language="ko", author_id=author)
    await repo.set_content_rating(book_id, "AGE18", {})

    content = await svc.get_content(book_id, account_id=author)  # 게이트 우회
    assert content.content_rating == "AGE18"


async def test_get_content_non_owner_still_blocked_when_book_has_author():
    """작가 있는 책 — 소유자 아닌 미인증 제3자는 여전히 차단(소유자 우회가 전체 우회로 새지 않음)."""
    author = uuid.uuid4()
    repo = FakeBookRepository()
    svc = BookService(repo, account_tier=_FakeAccountTier())
    book_id = await repo.create_book(title="내 원고", kind="BOOK", language="ko", author_id=author)
    await repo.set_content_rating(book_id, "AGE18", {})

    with pytest.raises(AgeVerificationRequired):
        await svc.get_content(book_id, account_id=uuid.uuid4())
