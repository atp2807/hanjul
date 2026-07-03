"""콘텐츠 연령등급 E2E — 기준 공개·소유권 게이트·503(키 미설정)·오버라이드."""
import httpx
import pytest
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import settings

settings.DEBUG = False

from main import app  # noqa: E402
from src.config.database import get_session  # noqa: E402
from src.features.auth.application.auth_service import AuthService  # noqa: E402
from src.features.auth.domain.models import SocialProfile  # noqa: E402
from src.features.auth.infrastructure.account_repo import SqlAccountRepository  # noqa: E402
from src.features.auth.presentation.dependencies import get_auth_service, token_issuer  # noqa: E402
from src.features.books.application.content_rating_service import ContentRatingService  # noqa: E402
from src.features.books.infrastructure.anthropic_rating_classifier import (  # noqa: E402
    AnthropicContentRatingClassifier,
)
from src.features.books.infrastructure.book_repo import SqlBookRepository  # noqa: E402
from src.features.books.presentation.dependencies import get_content_rating_service  # noqa: E402
from tests.fixtures.fake_account_repo import FakeProvider  # noqa: E402
from tests.fixtures.fake_rating_classifier import FakeContentRatingClassifier  # noqa: E402
from tests.integration.auth_helpers import login_account  # noqa: E402

PROFILE = SocialProfile("GOOGLE", "rater-x", "rater@x.com", "작가")


@pytest.fixture
def app_db(sessionmaker):
    async def _session():
        async with sessionmaker() as s:
            yield s

    def _auth(session: AsyncSession = Depends(get_session)):
        return AuthService(
            SqlAccountRepository(session), {"GOOGLE": FakeProvider("GOOGLE", PROFILE)}, token_issuer()
        )

    app.dependency_overrides[get_session] = _session
    app.dependency_overrides[get_auth_service] = _auth
    yield
    app.dependency_overrides.clear()


def _override_classifier(classifier):
    def _svc(session: AsyncSession = Depends(get_session)):
        return ContentRatingService(SqlBookRepository(session), classifier)

    app.dependency_overrides[get_content_rating_service] = _svc


async def test_criteria_public_no_auth(app_db):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/api/content-rating/criteria")
        assert r.status_code == 200
        body = r.json()
        assert body["tiers"] == ["ALL", "AGE12", "AGE15", "AGE18"]
        assert len(body["categories"]) == 8


async def test_suggest_owner_200_and_non_owner_403(app_db):
    _override_classifier(FakeContentRatingClassifier(result={"violence": "AGE15"}))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        token, _ = await login_account(c, "google", "x")
        auth = {"Authorization": f"Bearer {token}"}
        book = (await c.post("/api/books", json={"title": "내 책"}, headers=auth)).json()["bookId"]
        await c.post(f"/api/books/{book}/import", json={"rawText": "본문입니다"}, headers=auth)

        # 소유 작가 → 200
        r = await c.post(f"/api/books/{book}/content-rating/suggest", headers=auth)
        assert r.status_code == 200, r.text
        assert r.json()["contentRating"] == "AGE15"
        assert r.json()["contentRatingDetail"]["violence"] == "AGE15"

        # 작가 없는(익명) 책 → 소유자 아님 → 403
        anon = (await c.post("/api/books", json={"title": "익명책"})).json()["bookId"]
        r = await c.post(f"/api/books/{anon}/content-rating/suggest", headers=auth)
        assert r.status_code == 403


async def test_suggest_key_unconfigured_returns_503_not_500(app_db):
    """CONTENT_RATING_AI_DEMO=False + ANTHROPIC_API_KEY 미설정 → RuntimeError가 503으로."""
    _override_classifier(AnthropicContentRatingClassifier(api_key=""))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        token, _ = await login_account(c, "google", "x")
        auth = {"Authorization": f"Bearer {token}"}
        book = (await c.post("/api/books", json={"title": "내 책"}, headers=auth)).json()["bookId"]
        await c.post(f"/api/books/{book}/import", json={"rawText": "본문"}, headers=auth)
        r = await c.post(f"/api/books/{book}/content-rating/suggest", headers=auth)
        assert r.status_code == 503


async def test_set_rating_override_and_reflected_in_content(app_db):
    _override_classifier(FakeContentRatingClassifier())
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        token, _ = await login_account(c, "google", "x")
        auth = {"Authorization": f"Bearer {token}"}
        book = (await c.post("/api/books", json={"title": "내 책"}, headers=auth)).json()["bookId"]

        # 유효 오버라이드 → 200, 최종등급 반영
        r = await c.put(
            f"/api/books/{book}/content-rating",
            json={"detail": {"sexual": "AGE18", "language": "AGE12"}},
            headers=auth,
        )
        assert r.status_code == 200, r.text
        assert r.json()["contentRating"] == "AGE18"

        # 책 조회 응답(content)에 contentRating 반영
        content = (await c.get(f"/api/books/{book}/content", headers=auth)).json()
        assert content["contentRating"] == "AGE18"
        assert content["contentRatingDetail"]["sexual"] == "AGE18"

        # 잘못된 카테고리 → 422
        r = await c.put(
            f"/api/books/{book}/content-rating", json={"detail": {"nope": "AGE12"}}, headers=auth
        )
        assert r.status_code == 422
