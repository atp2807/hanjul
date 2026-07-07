"""작가 공개 프로필 E2E — bio 설정 + /authors/{id}(이름·소개·출판작)."""
import uuid

import pytest
from src.features.auth.domain.models import SocialProfile

from tests.integration.auth_helpers import login_account
from tests.integration.book_helpers import create_book


@pytest.fixture
def social_profile():
    return SocialProfile("GOOGLE", "auth-prof", "a@x.com", "작가한")


async def test_author_profile_bio_and_published_books(client):
    token, _ = await login_account(client, "google", "x")
    auth = {"Authorization": f"Bearer {token}"}
    author_id = (await client.get("/api/me", headers=auth)).json()["id"]

    # bio 설정
    assert (await client.put("/api/me/profile", json={"bio": "소설 쓰는 사람"}, headers=auth)).status_code == 204

    # 출판작 1
    book = await create_book(client, auth, title="내 소설")
    await client.put(f"/api/books/{book}/price", json={"amount": 5000}, headers=auth)
    await client.post(f"/api/books/{book}/publish-now", headers=auth)

    # 공개 프로필
    prof = (await client.get(f"/api/authors/{author_id}")).json()
    assert prof["displayName"] == "작가한"
    assert prof["bio"] == "소설 쓰는 사람"
    assert any(b["id"] == book for b in prof["books"])

    # 없는 작가 404
    assert (await client.get(f"/api/authors/{uuid.uuid4()}")).status_code == 404
