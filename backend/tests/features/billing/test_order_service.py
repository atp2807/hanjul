"""OrderService — 결제확인 → 정산 (Fake repo/gateway)."""
import uuid

import pytest

from src.features.billing.application.order_service import OrderService
from src.features.billing.domain.models import (
    PAID,
    AlreadyPaid,
    OrderNotFound,
    PaymentFailed,
)
from tests.fixtures.fake_order_repo import FakeGateway, FakeOrderRepository


def make_service(ok=True):
    repo = FakeOrderRepository()
    return OrderService(repo, FakeGateway(ok=ok)), repo


async def test_confirm_creates_settlement_with_correct_payout():
    svc, repo = make_service(ok=True)
    oid = await svc.create_order(uuid.uuid4(), uuid.uuid4(), 10000, "SELF")
    result = await svc.confirm_payment(oid, "tx-1")
    # SELF 10000 → 작가 7000, 원천 231, 지급 6769
    assert result.gross_amt == 7000
    assert result.withholding_amt == 231
    assert result.payout_amt == 6769
    assert repo.orders[oid].status_cd == PAID


async def test_double_confirm_raises_already_paid():
    svc, _ = make_service(ok=True)
    oid = await svc.create_order(uuid.uuid4(), uuid.uuid4(), 5000, "SELF")
    await svc.confirm_payment(oid, "tx-1")
    with pytest.raises(AlreadyPaid):
        await svc.confirm_payment(oid, "tx-2")


async def test_failed_verification_raises_and_keeps_pending():
    svc, repo = make_service(ok=False)
    oid = await svc.create_order(uuid.uuid4(), uuid.uuid4(), 5000, "SELF")
    with pytest.raises(PaymentFailed):
        await svc.confirm_payment(oid, "tx-bad")
    assert repo.orders[oid].status_cd == "PENDING"


async def test_confirm_unknown_order_raises():
    svc, _ = make_service()
    with pytest.raises(OrderNotFound):
        await svc.confirm_payment(uuid.uuid4(), "tx")


async def test_external_channel_uses_60_percent():
    svc, _ = make_service(ok=True)
    oid = await svc.create_order(uuid.uuid4(), uuid.uuid4(), 10000, "EXTERNAL")
    result = await svc.confirm_payment(oid, "tx")
    assert result.gross_amt == 6000
    assert result.payout_amt == 5802
