"""내 서재 E2E — 로그인 → 구매 → /me/library 에 등장."""
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
from src.features.billing.infrastructure.order_repo import SqlOrderRepository  # noqa: E402
from src.features.billing.presentation.dependencies import get_order_service  # noqa: E402
from tests.fixtures.fake_account_repo import FakeProvider  # noqa: E402
from tests.fixtures.fake_order_repo import FakeGateway  # noqa: E402

PROFILE = SocialProfile("GOOGLE", "lib-sub", "lib@x.com", "독자")


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
        return OrderService(SqlOrderRepository(session), FakeGateway(ok=True))

    app.dependency_overrides[get_session] = _session
    app.dependency_overrides[get_auth_service] = _auth
    app.dependency_overrides[get_order_service] = _order
    yield
    app.dependency_overrides.clear()


async def test_purchased_book_appears_in_library(app_db):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        login = (await c.get("/api/auth/google/callback?code=x")).json()
        token, me_id = login["token"], login["account"]["id"]
        auth = {"Authorization": f"Bearer {token}"}

        # 미로그인 → 401
        assert (await c.get("/api/me/library")).status_code == 401
        # 처음엔 빈 서재
        assert (await c.get("/api/me/library", headers=auth)).json() == []

        # 책 생성 → 구매 → 결제확인
        book_id = (await c.post("/api/books", json={"title": "산 책"})).json()["bookId"]
        order_id = (
            await c.post(
                "/api/orders",
                json={"bookId": book_id, "buyerAccountId": me_id, "amount": 8000, "channel": "SELF"},
            )
        ).json()["id"]
        await c.post(f"/api/orders/{order_id}/confirm", json={"pgTxId": "tx"})

        # 서재에 등장
        lib = (await c.get("/api/me/library", headers=auth)).json()
        assert len(lib) == 1
        assert lib[0]["bookId"] == book_id
        assert lib[0]["title"] == "산 책"
