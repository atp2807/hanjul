"""읽기 미리보기 게이팅 E2E — 유료책은 미구매=앞3블록, 구매=전체."""
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
from src.features.billing.application.order_service import OrderService  # noqa: E402
from src.features.billing.infrastructure.book_pricing import SqlBookPricing  # noqa: E402
from src.features.billing.infrastructure.order_repo import SqlOrderRepository  # noqa: E402
from src.features.billing.presentation.dependencies import get_order_service  # noqa: E402
from tests.fixtures.fake_account_repo import FakeProvider  # noqa: E402
from tests.fixtures.fake_order_repo import FakeGateway  # noqa: E402
from tests.integration.auth_helpers import login_account  # noqa: E402

PROFILE = SocialProfile("GOOGLE", "g-sub", "g@x.com", "독자")


def _count_blocks(content):
    return sum(len(ch["blocks"]) for ch in content["chapters"])


@pytest.fixture
def app_db(sessionmaker):
    async def _session():
        async with sessionmaker() as s:
            yield s

    def _auth(session: AsyncSession = Depends(get_session)):
        return AuthService(
            SqlAccountRepository(session), {"GOOGLE": FakeProvider("GOOGLE", PROFILE)}, token_issuer()
        )

    def _order(session: AsyncSession = Depends(get_session)):
        return OrderService(SqlOrderRepository(session), FakeGateway(ok=True), SqlBookPricing(session))

    app.dependency_overrides[get_session] = _session
    app.dependency_overrides[get_auth_service] = _auth
    app.dependency_overrides[get_order_service] = _order
    yield
    app.dependency_overrides.clear()


async def test_preview_for_non_owner_full_for_owner(app_db):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        # 5블록짜리 유료책 준비 (작가 인증으로 생성 → 변경 권한)
        token, _ = await login_account(c, "google", "x")
        auth = {"Authorization": f"Bearer {token}"}
        book_id = (await c.post("/api/books", json={"title": "유료책"}, headers=auth)).json()["bookId"]
        await c.post(f"/api/books/{book_id}/import", json={"rawText": "1\n\n2\n\n3\n\n4\n\n5"}, headers=auth)
        await c.put(f"/api/books/{book_id}/price", json={"amount": 5000}, headers=auth)
        await c.post(f"/api/books/{book_id}/submit", headers=auth)
        await c.post(f"/api/books/{book_id}/publish", headers=auth)

        # 미로그인 → 미리보기 3블록
        anon = (await c.get(f"/api/books/{book_id}/content")).json()
        assert anon["isPreview"] is True
        assert _count_blocks(anon) == 3

        # 로그인했지만 미구매 → 여전히 미리보기
        token, me = await login_account(c, "google", "x")
        me_id = me["id"]
        auth = {"Authorization": f"Bearer {token}"}
        before = (await c.get(f"/api/books/{book_id}/content", headers=auth)).json()
        assert before["isPreview"] is True and _count_blocks(before) == 3

        # 구매 후 → 전체 (금액은 서버 도출)
        order_id = (
            await c.post("/api/orders", json={"bookId": book_id, "withdrawalConsent": True}, headers=auth)
        ).json()["id"]
        await c.post(f"/api/orders/{order_id}/confirm", json={"pgTxId": "tx"}, headers=auth)

        after = (await c.get(f"/api/books/{book_id}/content", headers=auth)).json()
        assert after["isPreview"] is False
        assert _count_blocks(after) == 5


async def test_free_book_is_full_without_login(app_db):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        book_id = (await c.post("/api/books", json={"title": "무료책"})).json()["bookId"]
        await c.post(f"/api/books/{book_id}/import", json={"rawText": "1\n\n2\n\n3\n\n4"})
        # 가격 미설정(무료) → 미로그인도 전체
        res = (await c.get(f"/api/books/{book_id}/content")).json()
        assert res["isPreview"] is False
        assert _count_blocks(res) == 4
