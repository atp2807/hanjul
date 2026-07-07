"""스토어 카테고리 탐색 — ?category= 로 장르 필터."""
import pytest
from src.features.auth.domain.models import SocialProfile

from tests.integration.auth_helpers import login_account
from tests.integration.book_helpers import create_book


@pytest.fixture
def social_profile():
    return SocialProfile("GOOGLE", "store-a", "a@x.com", "작가")


async def test_store_filter_by_category(client):
    a_auth = {"Authorization": f"Bearer {(await login_account(client, 'google', 'a'))[0]}"}

    async def make(title, category):
        bid = await create_book(client, a_auth, title=title)
        await client.put(f"/api/books/{bid}/meta", json={"category": category}, headers=a_auth)
        await client.put(f"/api/books/{bid}/price", json={"amount": 1000}, headers=a_auth)
        await client.post(f"/api/books/{bid}/publish-now", headers=a_auth)

    await make("소설가게책", "소설")
    await make("에세이가게책", "에세이")

    # 전체 — 카테고리 노출
    allb = (await client.get("/api/store/books")).json()["items"]
    by = {x["title"]: x for x in allb}
    assert by["소설가게책"]["category"] == "소설"

    # 카테고리 필터
    only = (await client.get("/api/store/books?category=소설")).json()["items"]
    titles = [x["title"] for x in only]
    assert "소설가게책" in titles and "에세이가게책" not in titles
