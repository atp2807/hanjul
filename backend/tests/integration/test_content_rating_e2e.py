"""콘텐츠 연령등급 E2E — 기준 공개·소유권 게이트·503(키 미설정)·오버라이드."""
import pytest
from fastapi import Depends
from main import app
from sqlalchemy.ext.asyncio import AsyncSession
from src.config.database import get_session
from src.features.auth.domain.models import SocialProfile
from src.features.books.application.content_rating_service import ContentRatingService
from src.features.books.infrastructure.anthropic_rating_classifier import (
    AnthropicContentRatingClassifier,
)
from src.features.books.infrastructure.book_repo import SqlBookRepository
from src.features.books.presentation.dependencies import get_content_rating_service

from tests.fixtures.fake_rating_classifier import FakeContentRatingClassifier
from tests.integration.auth_helpers import login_account
from tests.integration.book_helpers import create_book


@pytest.fixture
def social_profile():
    return SocialProfile("GOOGLE", "rater-x", "rater@x.com", "작가")


def _override_classifier(classifier):
    def _svc(session: AsyncSession = Depends(get_session)):
        return ContentRatingService(SqlBookRepository(session), classifier)

    app.dependency_overrides[get_content_rating_service] = _svc


async def test_criteria_public_no_auth(client):
    r = await client.get("/api/content-rating/criteria")
    assert r.status_code == 200
    body = r.json()
    assert body["tiers"] == ["ALL", "AGE12", "AGE15", "AGE18"]
    assert len(body["categories"]) == 8


async def test_suggest_owner_200_and_non_owner_403(client):
    _override_classifier(FakeContentRatingClassifier(result={"violence": "AGE15"}))
    token, _ = await login_account(client, "google", "x")
    auth = {"Authorization": f"Bearer {token}"}
    book = await create_book(client, auth, title="내 책")
    await client.post(f"/api/books/{book}/import", json={"rawText": "본문입니다"}, headers=auth)

    # 소유 작가 → 200
    r = await client.post(f"/api/books/{book}/content-rating/suggest", headers=auth)
    assert r.status_code == 200, r.text
    assert r.json()["contentRating"] == "AGE15"
    assert r.json()["contentRatingDetail"]["violence"] == "AGE15"

    # 작가 없는(익명) 책 → 소유자 아님 → 403
    anon = await create_book(client, title="익명책")
    r = await client.post(f"/api/books/{anon}/content-rating/suggest", headers=auth)
    assert r.status_code == 403


async def test_suggest_key_unconfigured_returns_503_not_500(client):
    """CONTENT_RATING_AI_DEMO=False + ANTHROPIC_API_KEY 미설정 → RuntimeError가 503으로."""
    _override_classifier(AnthropicContentRatingClassifier(api_key=""))
    token, _ = await login_account(client, "google", "x")
    auth = {"Authorization": f"Bearer {token}"}
    book = await create_book(client, auth, title="내 책")
    await client.post(f"/api/books/{book}/import", json={"rawText": "본문"}, headers=auth)
    r = await client.post(f"/api/books/{book}/content-rating/suggest", headers=auth)
    assert r.status_code == 503


async def test_set_rating_override_and_reflected_in_content(client):
    _override_classifier(FakeContentRatingClassifier())
    token, _ = await login_account(client, "google", "x")
    auth = {"Authorization": f"Bearer {token}"}
    book = await create_book(client, auth, title="내 책")

    # 유효 오버라이드 → 200, 최종등급 반영
    r = await client.put(
        f"/api/books/{book}/content-rating",
        json={"detail": {"sexual": "AGE18", "language": "AGE12"}},
        headers=auth,
    )
    assert r.status_code == 200, r.text
    assert r.json()["contentRating"] == "AGE18"

    # 책 조회 응답(content)에 contentRating 반영
    content = (await client.get(f"/api/books/{book}/content", headers=auth)).json()
    assert content["contentRating"] == "AGE18"
    assert content["contentRatingDetail"]["sexual"] == "AGE18"

    # 잘못된 카테고리 → 422
    r = await client.put(
        f"/api/books/{book}/content-rating", json={"detail": {"nope": "AGE12"}}, headers=auth
    )
    assert r.status_code == 422
