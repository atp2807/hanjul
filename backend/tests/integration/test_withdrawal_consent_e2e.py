"""청약철회 제한 동의 게이트 (전자상거래법 §17⑥) — 미동의 주문 거부 + 동의 시각 기록."""
import pytest
from sqlalchemy import select
from src.features.auth.domain.models import SocialProfile
from src.infrastructure.db.models.book import Block, Book, Chapter
from src.infrastructure.db.models.order import Order

from tests.integration.auth_helpers import login_token

BUYER = SocialProfile("GOOGLE", "buyer-sub", "buyer@x.com", "구매자")


@pytest.fixture
def social_profile():
    return BUYER


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


async def test_order_without_consent_rejected(client, app_db):
    token, _ = await login_token(client, "google", "x")
    hdr = {"Authorization": f"Bearer {token}"}
    book = await _make_paid_book(app_db)

    # 동의 없음(기본값 false) → 422
    r = await client.post("/api/orders", json={"bookId": book}, headers=hdr)
    assert r.status_code == 422, r.text
    # 명시적 false → 422
    r2 = await client.post("/api/orders", json={"bookId": book, "withdrawalConsent": False}, headers=hdr)
    assert r2.status_code == 422


async def test_order_with_consent_records_timestamp(client, app_db):
    token, _ = await login_token(client, "google", "x")
    hdr = {"Authorization": f"Bearer {token}"}
    book = await _make_paid_book(app_db)

    r = await client.post("/api/orders", json={"bookId": book, "withdrawalConsent": True}, headers=hdr)
    assert r.status_code == 201, r.text

    # 동의 시각이 주문에 기록됨(분쟁 입증용)
    async with app_db() as s:
        order = (await s.execute(select(Order))).scalar_one()
        assert order.withdrawal_consent_at is not None
