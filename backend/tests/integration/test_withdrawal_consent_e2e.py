"""청약철회 제한 동의 게이트 (전자상거래법 §17⑥) — 미동의 주문 거부 + 동의 시각 기록."""
import httpx
import pytest
from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import settings

settings.DEBUG = False

from main import app  # noqa: E402
from src.config.database import get_session  # noqa: E402
from src.features.auth.application.auth_service import AuthService  # noqa: E402
from src.features.auth.domain.models import SocialProfile  # noqa: E402
from src.features.auth.infrastructure.account_repo import SqlAccountRepository  # noqa: E402
from src.features.auth.presentation.dependencies import get_auth_service, token_issuer  # noqa: E402
from src.infrastructure.db.models.book import Block, Book, Chapter  # noqa: E402
from src.infrastructure.db.models.order import Order  # noqa: E402
from tests.fixtures.fake_account_repo import FakeProvider  # noqa: E402
from tests.integration.auth_helpers import login_token  # noqa: E402

BUYER = SocialProfile("GOOGLE", "buyer-sub", "buyer@x.com", "구매자")


@pytest.fixture
def app_db(sessionmaker):
    async def _session():
        async with sessionmaker() as s:
            yield s

    def _auth(session: AsyncSession = Depends(get_session)):
        return AuthService(
            SqlAccountRepository(session), {"GOOGLE": FakeProvider("GOOGLE", BUYER)}, token_issuer()
        )

    app.dependency_overrides[get_session] = _session
    app.dependency_overrides[get_auth_service] = _auth
    yield sessionmaker
    app.dependency_overrides.clear()


async def _make_paid_book(sessionmaker) -> str:
    async with sessionmaker() as s:
        book = Book(title="유료책", kind="BOOK", language="ko", status="PUBLISHED", price_amt=5000)
        s.add(book)
        await s.flush()
        ch = Chapter(book_id=book.id, order_no=0, title="1장")
        s.add(ch)
        await s.flush()
        s.add(Block(chapter_id=ch.id, order_no=0, block_type="P", html="<p>본문</p>"))
        await s.commit()
        return str(book.id)


def _client():
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t")


async def test_order_without_consent_rejected(app_db):
    async with _client() as c:
        token, _ = await login_token(c, "google", "x")
        hdr = {"Authorization": f"Bearer {token}"}
        book = await _make_paid_book(app_db)

        # 동의 없음(기본값 false) → 422
        r = await c.post("/api/orders", json={"bookId": book}, headers=hdr)
        assert r.status_code == 422, r.text
        # 명시적 false → 422
        r2 = await c.post("/api/orders", json={"bookId": book, "withdrawalConsent": False}, headers=hdr)
        assert r2.status_code == 422


async def test_order_with_consent_records_timestamp(app_db):
    async with _client() as c:
        token, _ = await login_token(c, "google", "x")
        hdr = {"Authorization": f"Bearer {token}"}
        book = await _make_paid_book(app_db)

        r = await c.post("/api/orders", json={"bookId": book, "withdrawalConsent": True}, headers=hdr)
        assert r.status_code == 201, r.text

        # 동의 시각이 주문에 기록됨(분쟁 입증용)
        async with app_db() as s:
            order = (await s.execute(select(Order))).scalar_one()
            assert order.withdrawal_consent_at is not None
