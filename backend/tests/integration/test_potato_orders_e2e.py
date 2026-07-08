"""운영자 주문 환불 집행(potato Phase 2, A) E2E — buyer 제약 없이 임의 주문 환불 + 감사."""
from datetime import UTC, datetime
from uuid import UUID, uuid4

import httpx
import pytest
from fastapi import Depends
from main import app
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.config.database import get_potato_session, get_session
from src.features.billing.infrastructure.book_pricing import SqlBookPricing
from src.features.billing.infrastructure.order_repo import SqlOrderRepository
from src.features.billing.presentation.dependencies import get_order_service
from src.features.potato.application.password import hash_password
from src.features.potato.domain.models import OPERATOR
from src.features.potato.infrastructure.operator_repo import SqlOperatorRepository
from src.infrastructure.db.models.account import Account
from src.infrastructure.db.models.book import Book
from src.infrastructure.db.models.operator import AuditLog
from src.infrastructure.db.models.order import Order

from tests.fixtures.fake_order_repo import FakeGateway

EMAIL = "orderop@hanjul.io"
PASSWORD = "potato-order-123"


@pytest.fixture
def app_db_potato_orders(sessionmaker):
    """app_db_potato + get_order_service 오버라이드(FakeGateway 항상 승인) — 환불 집행 E2E용."""
    async def _session():
        async with sessionmaker() as s:
            yield s

    def _order(session: AsyncSession = Depends(get_session)):
        from src.features.billing.application.order_service import OrderService

        return OrderService(SqlOrderRepository(session), FakeGateway(ok=True), SqlBookPricing(session))

    app.dependency_overrides[get_session] = _session
    app.dependency_overrides[get_potato_session] = _session
    app.dependency_overrides[get_order_service] = _order
    yield sessionmaker
    app.dependency_overrides.clear()


async def _op_token(c, sessionmaker) -> str:
    async with sessionmaker() as s:
        await SqlOperatorRepository(s).create(
            email=EMAIL, name="운영자", role=OPERATOR, password_hash=hash_password(PASSWORD)
        )
    r = await c.post("/api/potato/auth/login", json={"email": EMAIL, "password": PASSWORD})
    return r.json()["token"]


async def _seed_paid_order(sessionmaker, amount=5000) -> tuple[str, str]:
    """PUBLISHED 책 + PAID 주문(구매자 계정 실존) 1건 — 반환은 (order_id, buyer_id)."""
    book_id, buyer_id = uuid4(), uuid4()
    async with sessionmaker() as s:
        s.add(
            Book(
                id=book_id, title="환불 대상 책", kind="BOOK", language="ko", status="PUBLISHED",
                price_amt=amount, published_at=datetime.now(UTC),
            )
        )
        s.add(Account(id=buyer_id, email="buyer@x.com", display_name="구매자", role="READER"))
        order = Order(
            book_id=book_id, buyer_account_id=buyer_id, amount_amt=amount, channel="SELF",
            status="PAID", paid_at=datetime.now(UTC), pg_tx_id="tx-1",
        )
        s.add(order)
        await s.commit()
        return str(order.id), str(buyer_id)


def _client():
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app, client=("127.0.0.1", 50000)), base_url="http://t"
    )


async def test_operator_refund_marks_refunded_and_audits(app_db_potato_orders):
    async with _client() as c:
        hdr = {"Authorization": f"Bearer {await _op_token(c, app_db_potato_orders)}"}
        order_id, buyer_id = await _seed_paid_order(app_db_potato_orders)

        # 운영자 주문 목록에 PAID로 보임 (환불 대상 탐색)
        listed = (await c.get("/api/potato/orders", headers=hdr, params={"status": "PAID"})).json()
        assert any(o["id"] == order_id for o in listed)
        target = next(o for o in listed if o["id"] == order_id)
        assert target["buyerAccountId"] == buyer_id
        assert target["bookTitle"] == "환불 대상 책"
        assert target["amountAmt"] == 5000

        # 운영자 환불 집행 — buyer 제약 없음
        r = await c.post(
            f"/api/potato/orders/{order_id}/refund", headers=hdr, json={"reason": "고객 요청"}
        )
        assert r.status_code == 204, r.text

        # DB 상태 REFUNDED
        async with app_db_potato_orders() as s:
            order = (
                await s.execute(select(Order).where(Order.id == UUID(order_id)))
            ).scalar_one()
            assert order.status == "REFUNDED"
            assert order.refunded_at is not None

            rows = (await s.execute(select(AuditLog))).scalars().all()
        assert len(rows) == 1
        assert rows[0].action == "ORDER_REFUND"
        assert rows[0].entity_type == "ORDER"
        assert str(rows[0].entity_id) == order_id
        assert rows[0].detail == {"reason": "고객 요청"}

        # 목록에서도 상태 반영 — PAID 필터엔 더이상 안 보임
        still_paid = (await c.get("/api/potato/orders", headers=hdr, params={"status": "PAID"})).json()
        assert all(o["id"] != order_id for o in still_paid)
        refunded = (await c.get("/api/potato/orders", headers=hdr, params={"status": "REFUNDED"})).json()
        assert any(o["id"] == order_id for o in refunded)


async def test_operator_refund_already_refunded_conflicts(app_db_potato_orders):
    async with _client() as c:
        hdr = {"Authorization": f"Bearer {await _op_token(c, app_db_potato_orders)}"}
        order_id, _ = await _seed_paid_order(app_db_potato_orders)

        assert (
            await c.post(f"/api/potato/orders/{order_id}/refund", headers=hdr, json={})
        ).status_code == 204
        # 이미 환불된 주문 재환불 → 409(NotRefundable)
        r = await c.post(f"/api/potato/orders/{order_id}/refund", headers=hdr, json={})
        assert r.status_code == 409, r.text


async def test_refund_and_orders_list_require_operator_token(app_db_potato_orders):
    async with _client() as c:
        order_id, _ = await _seed_paid_order(app_db_potato_orders)

        assert (await c.get("/api/potato/orders")).status_code == 401
        assert (await c.post(f"/api/potato/orders/{order_id}/refund", json={})).status_code == 401
