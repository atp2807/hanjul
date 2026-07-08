"""GET /sitemap.xml — api_router(/api) 밖 루트 경로. main.py 직접 등록 확인."""
import pytest
from src.config.settings import settings
from src.features.auth.domain.models import SocialProfile

from tests.integration.auth_helpers import login_account
from tests.integration.book_helpers import publish_priced_book


@pytest.fixture
def social_profile():
    return SocialProfile("GOOGLE", "sitemap-author", "sitemap@x.com", "작가")


async def test_sitemap_200_xml_with_static_and_book_urls(client):
    auth = {"Authorization": f"Bearer {(await login_account(client, 'google', 'sitemap-author'))[0]}"}
    book_id = await publish_priced_book(client, auth, title="사이트맵책", price=1000)

    r = await client.get("/sitemap.xml")

    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/xml")
    assert "<urlset" in r.text
    assert f"{settings.FRONTEND_URL}/books/{book_id}" in r.text
