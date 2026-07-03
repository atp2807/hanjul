"""ContentRatingService 유스케이스 테스트 (Fake repo + Fake classifier)."""
import uuid

import pytest

from src.features.books.application.content_rating_service import ContentRatingService
from src.features.books.domain.content_rating import InvalidRatingInput, category_keys
from src.features.books.domain.models import BookNotFound, NotOwner
from tests.fixtures.fake_book_repo import FakeBookRepository
from tests.fixtures.fake_rating_classifier import FakeContentRatingClassifier


async def _book_with_content(repo, author):
    book_id = await repo.create_book(title="책", kind="BOOK", language="ko", author_id=author)
    await repo.add_chapter_with_blocks(book_id, "1장", [{"type": "P", "html": "<p>칼부림</p>"}])
    return book_id


async def test_suggest_saves_detail_and_overall_max():
    repo = FakeBookRepository()
    author = uuid.uuid4()
    book_id = await _book_with_content(repo, author)
    clf = FakeContentRatingClassifier(result={"violence": "AGE15", "sexual": "AGE18"})
    svc = ContentRatingService(repo, clf)

    rating, detail = await svc.suggest_rating(book_id, author)

    assert rating == "AGE18"  # 8기준 중 최댓값
    assert set(detail.keys()) == set(category_keys())
    assert detail["violence"] == "AGE15"
    # DB 저장 확인 (get_content로 되읽음)
    content = await repo.get_content(book_id)
    assert content.content_rating == "AGE18"
    assert content.content_rating_detail["sexual"] == "AGE18"


async def test_suggest_truncates_text_to_budget():
    repo = FakeBookRepository()
    author = uuid.uuid4()
    book_id = await repo.create_book(title="긴책", kind="BOOK", language="ko", author_id=author)
    await repo.add_chapter_with_blocks(book_id, None, [{"type": "P", "html": "<p>" + "가" * 10000 + "</p>"}])
    clf = FakeContentRatingClassifier()
    svc = ContentRatingService(repo, clf)

    await svc.suggest_rating(book_id, author)
    assert len(clf.calls[0]) <= 6000  # MAX_CLASSIFY_CHARS 컷


async def test_suggest_rejects_non_owner():
    repo = FakeBookRepository()
    author = uuid.uuid4()
    book_id = await _book_with_content(repo, author)
    svc = ContentRatingService(repo, FakeContentRatingClassifier())
    with pytest.raises(NotOwner):
        await svc.suggest_rating(book_id, uuid.uuid4())


async def test_suggest_unknown_book_raises():
    svc = ContentRatingService(FakeBookRepository(), FakeContentRatingClassifier())
    with pytest.raises(BookNotFound):
        await svc.suggest_rating(uuid.uuid4(), uuid.uuid4())


async def test_set_rating_merges_partial_override():
    repo = FakeBookRepository()
    author = uuid.uuid4()
    book_id = await _book_with_content(repo, author)
    svc = ContentRatingService(repo, FakeContentRatingClassifier())
    # 먼저 자동분류로 기존값 심기
    await svc.suggest_rating(book_id, author)  # 전부 ALL
    # 일부만 오버라이드
    rating, detail = await svc.set_rating(book_id, author, {"language": "AGE12"})
    assert detail["language"] == "AGE12"
    assert rating == "AGE12"
    # 다시 다른 카테고리 추가 오버라이드 → 기존 language 유지
    rating, detail = await svc.set_rating(book_id, author, {"violence": "AGE18"})
    assert detail["language"] == "AGE12"  # 병합됨
    assert detail["violence"] == "AGE18"
    assert rating == "AGE18"


async def test_set_rating_invalid_category_raises_422_domain():
    repo = FakeBookRepository()
    author = uuid.uuid4()
    book_id = await _book_with_content(repo, author)
    svc = ContentRatingService(repo, FakeContentRatingClassifier())
    with pytest.raises(InvalidRatingInput):
        await svc.set_rating(book_id, author, {"nope": "AGE12"})


async def test_set_rating_invalid_tier_raises_422_domain():
    repo = FakeBookRepository()
    author = uuid.uuid4()
    book_id = await _book_with_content(repo, author)
    svc = ContentRatingService(repo, FakeContentRatingClassifier())
    with pytest.raises(InvalidRatingInput):
        await svc.set_rating(book_id, author, {"violence": "AGE7"})


async def test_suggest_rejects_bad_classifier_output():
    repo = FakeBookRepository()
    author = uuid.uuid4()
    book_id = await _book_with_content(repo, author)
    # 분류기가 이상한 tier를 반환 → 조용히 기본값 넣지 말고 실패
    clf = FakeContentRatingClassifier(result={"violence": "BOGUS"})
    svc = ContentRatingService(repo, clf)
    with pytest.raises(InvalidRatingInput):
        await svc.suggest_rating(book_id, author)
