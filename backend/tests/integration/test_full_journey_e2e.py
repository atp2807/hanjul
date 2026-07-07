"""풀 유저 저니 E2E — 작가가 출판하고 독자가 사서 읽기까지 한 줄로.

HTTP(httpx ASGITransport) → 서비스 → 실 레포 → DB(SQLite). 외부(소셜/PG/표지)만 Fake 주입.
한 시나리오로 전 피처(auth·books·catalog·billing·cover)가 함께 도는지 검증.
"""
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
from src.features.cover.application.cover_service import CoverService  # noqa: E402
from src.features.cover.infrastructure.cover_repo import SqlCoverRepository  # noqa: E402
from src.features.cover.presentation.dependencies import get_cover_service  # noqa: E402

from tests.fixtures.fake_account_repo import FakeProvider  # noqa: E402
from tests.fixtures.fake_cover import FakeCoverGenerator  # noqa: E402
from tests.fixtures.fake_order_repo import FakeGateway  # noqa: E402
from tests.integration.auth_helpers import login_account  # noqa: E402

AUTHOR = SocialProfile("GOOGLE", "author-sub", "author@x.com", "박작가")
BUYER = SocialProfile("NAVER", "buyer-sub", "buyer@x.com", "독자")


@pytest.fixture
def journey(sessionmaker):
    async def _session():
        async with sessionmaker() as s:
            yield s

    def _auth(session: AsyncSession = Depends(get_session)):
        return AuthService(
            SqlAccountRepository(session),
            {"GOOGLE": FakeProvider("GOOGLE", AUTHOR), "NAVER": FakeProvider("NAVER", BUYER)},
            token_issuer(),
        )

    def _order(session: AsyncSession = Depends(get_session)):
        return OrderService(SqlOrderRepository(session), FakeGateway(ok=True), SqlBookPricing(session))

    def _cover(session: AsyncSession = Depends(get_session)):
        return CoverService(SqlCoverRepository(session), FakeCoverGenerator("https://img/cover.png"))

    app.dependency_overrides[get_session] = _session
    app.dependency_overrides[get_auth_service] = _auth
    app.dependency_overrides[get_order_service] = _order
    app.dependency_overrides[get_cover_service] = _cover
    yield
    app.dependency_overrides.clear()


async def test_author_publishes_reader_buys_and_reads(journey):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        # 1) 작가 · 독자 소셜 로그인 (서로 다른 provider → 다른 계정)
        author_token, author = await login_account(c, "google", "a")
        buyer_token, buyer = await login_account(c, "naver", "b")
        assert author["role"] == "READER"
        author_id, buyer_id = author["id"], buyer["id"]
        assert author_id != buyer_id
        author_auth = {"Authorization": f"Bearer {author_token}"}
        buyer_auth = {"Authorization": f"Bearer {buyer_token}"}

        # 2) 작가: 책 생성(소유) → 원고 import → 가격 → 심사 → 출판
        book_id = (await c.post("/api/books", json={"title": "한 줄"}, headers=author_auth)).json()["bookId"]
        imp = (await c.post(f"/api/books/{book_id}/import", json={"rawText": "# 1장\n\n본문입니다."}, headers=author_auth)).json()
        assert imp["blockCount"] == 2
        assert (await c.put(f"/api/books/{book_id}/price", json={"amount": 10000}, headers=author_auth)).status_code == 204
        assert (await c.post(f"/api/books/{book_id}/submit", headers=author_auth)).status_code == 204
        assert (await c.post(f"/api/books/{book_id}/publish", headers=author_auth)).status_code == 204

        # 3) 스토어에 공개로 노출
        store = (await c.get("/api/store/books")).json()
        assert any(
            i["id"] == book_id and i["status"] == "PUBLISHED" and i["priceAmt"] == 10000
            for i in store["items"]
        )

        # 4) 독자: 주문 → 결제확인 → 정산 (자체 70% + 3.3% 원천)
        # 금액은 안 보냄 — 서버가 책 가격(10000)에서 도출
        order_id = (
            await c.post("/api/orders", json={"bookId": book_id, "channel": "SELF", "withdrawalConsent": True}, headers=buyer_auth)
        ).json()["id"]
        settle = (
            await c.post(f"/api/orders/{order_id}/confirm", json={"pgTxId": "tx-1"}, headers=buyer_auth)
        ).json()
        assert settle["grossAmt"] == 7000
        assert settle["withholdingAmt"] == 231
        assert settle["payoutAmt"] == 6769
        assert (await c.get(f"/api/orders/{order_id}", headers=buyer_auth)).json()["status"] == "PAID"

        # 5) 독자: 본문 읽기 (정본 HTML)
        content = (await c.get(f"/api/books/{book_id}/content")).json()
        assert content["chapters"][0]["blocks"][0]["html"] == "<h1>1장</h1>"

        # 6) AI 표지 생성 → 스토어 상세에 반영
        cover = (await c.post(f"/api/books/{book_id}/cover", json={"prompt": "잔잔한 표지"}, headers=author_auth)).json()
        assert cover["coverUrl"] == "https://img/cover.png"
        detail = (await c.get(f"/api/store/books/{book_id}")).json()
        assert detail["coverUrl"] == "https://img/cover.png"
