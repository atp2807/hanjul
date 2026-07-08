"""OrderService — 구매(서버 금액 도출) + 결제확인 → 정산 (Fake)."""
import uuid

import pytest
from src.features.billing.application.order_service import OrderService
from src.features.billing.domain.models import (
    PAID,
    AlreadyOwned,
    AlreadyPaid,
    NotPurchasable,
    OrderNotFound,
    PaymentFailed,
)
from src.features.books.domain.content_rating import AgeVerificationRequired

from tests.fixtures.fake_order_repo import (
    FakeAccountTier,
    FakeGateway,
    FakeOrderRepository,
    FakePricing,
)


def make_service(ok=True, price=10000):
    repo = FakeOrderRepository()
    return OrderService(repo, FakeGateway(ok=ok), FakePricing(price)), repo


async def test_confirm_creates_settlement_with_server_price():
    svc, repo = make_service(ok=True, price=10000)
    # 금액은 클라가 아니라 서버 가격(10000)에서 도출
    oid = await svc.create_order(uuid.uuid4(), uuid.uuid4(), "SELF", withdrawal_consent=True)
    result = await svc.confirm_payment(oid, "tx-1")
    assert result.gross_amt == 7000
    assert result.withholding_amt == 231
    assert result.payout_amt == 6769
    assert repo.orders[oid].status == PAID
    assert repo.orders[oid].amount_amt == 10000  # 서버 가격이 박힘


async def test_not_purchasable_when_no_price():
    svc, _ = make_service(price=None)  # 미출판/미가격 → 구매 불가
    with pytest.raises(NotPurchasable):
        await svc.create_order(uuid.uuid4(), uuid.uuid4(), "SELF", withdrawal_consent=True)


async def test_cannot_buy_twice():
    svc, _ = make_service(price=5000)
    book, buyer = uuid.uuid4(), uuid.uuid4()
    oid = await svc.create_order(book, buyer, "SELF", withdrawal_consent=True)
    await svc.confirm_payment(oid, "tx")
    with pytest.raises(AlreadyOwned):  # 이미 소유 → 재구매 거부
        await svc.create_order(book, buyer, "SELF", withdrawal_consent=True)


async def test_double_confirm_raises_already_paid():
    svc, _ = make_service(price=5000)
    oid = await svc.create_order(uuid.uuid4(), uuid.uuid4(), "SELF", withdrawal_consent=True)
    await svc.confirm_payment(oid, "tx-1")
    with pytest.raises(AlreadyPaid):
        await svc.confirm_payment(oid, "tx-2")


async def test_failed_verification_keeps_pending():
    svc, repo = make_service(ok=False, price=5000)
    oid = await svc.create_order(uuid.uuid4(), uuid.uuid4(), "SELF", withdrawal_consent=True)
    with pytest.raises(PaymentFailed):
        await svc.confirm_payment(oid, "tx-bad")
    assert repo.orders[oid].status == "PENDING"


async def test_confirm_unknown_order_raises():
    svc, _ = make_service()
    with pytest.raises(OrderNotFound):
        await svc.confirm_payment(uuid.uuid4(), "tx")


async def test_external_channel_uses_60_percent():
    svc, _ = make_service(ok=True, price=10000)
    oid = await svc.create_order(uuid.uuid4(), uuid.uuid4(), "EXTERNAL", withdrawal_consent=True)
    result = await svc.confirm_payment(oid, "tx")
    assert result.gross_amt == 6000
    assert result.payout_amt == 5802


async def test_confirm_rejects_other_buyers_order():
    svc, _ = make_service(price=5000)
    oid = await svc.create_order(uuid.uuid4(), uuid.uuid4(), "SELF", withdrawal_consent=True)
    with pytest.raises(OrderNotFound):  # 남의 주문 confirm → 못 본 것처럼
        await svc.confirm_payment(oid, "tx", buyer_id=uuid.uuid4())


async def test_owns_reflects_payment():
    svc, _ = make_service(price=5000)
    book, buyer = uuid.uuid4(), uuid.uuid4()
    oid = await svc.create_order(book, buyer, "SELF", withdrawal_consent=True)
    assert await svc.owns(buyer, book) is False
    await svc.confirm_payment(oid, "tx")
    assert await svc.owns(buyer, book) is True


# ── 연령 게이트(dc-daeb0d3d) — 구매(주문생성) ────────────
def _svc_with_gate(price=10000, rating="ALL", tiers=None):
    repo = FakeOrderRepository()
    pricing = FakePricing(price, rating=rating)
    svc = OrderService(
        repo, FakeGateway(ok=True), pricing,
        rating_lookup=pricing, account_tier=FakeAccountTier(tiers),
    )
    return svc, repo


async def test_create_order_no_gate_ports_at_all_behaves_like_all_rated():
    """rating_lookup/account_tier 둘 다 미주입 — 등급조회 자체를 안 해 "ALL vs ALL" 통과.

    (구성한 FakePricing.rating="AGE18"은 rating_lookup으로 넘기지 않는 한 안 쓰인다 —
    즉 이건 "게이트가 꺼짐"이 아니라 "포트 없이는 등급을 모르니 안전한 기본값(ALL)으로
    되돌아간다"는 뜻. 기존 Fake 기반 단위테스트가 이 경로로 하위호환된다.)
    """
    svc = OrderService(FakeOrderRepository(), FakeGateway(ok=True), FakePricing(10000, rating="AGE18"))
    oid = await svc.create_order(uuid.uuid4(), uuid.uuid4(), "SELF", withdrawal_consent=True)
    assert oid is not None


async def test_create_order_rating_lookup_only_still_blocks_restricted_book():
    """account_tier 포트가 없어도(tier 기본값 ALL) rating_lookup만 있으면 게이트가 작동한다."""
    repo = FakeOrderRepository()
    pricing = FakePricing(10000, rating="AGE18")
    svc = OrderService(repo, FakeGateway(ok=True), pricing, rating_lookup=pricing)
    with pytest.raises(AgeVerificationRequired):
        await svc.create_order(uuid.uuid4(), uuid.uuid4(), "SELF", withdrawal_consent=True)


async def test_create_order_blocks_unverified_buyer_for_restricted_book():
    svc, _ = _svc_with_gate(rating="AGE18")
    with pytest.raises(AgeVerificationRequired):
        await svc.create_order(uuid.uuid4(), uuid.uuid4(), "SELF", withdrawal_consent=True)


async def test_create_order_allows_verified_buyer_for_restricted_book():
    buyer = uuid.uuid4()
    svc, repo = _svc_with_gate(rating="AGE18", tiers={buyer: "AGE18"})
    oid = await svc.create_order(uuid.uuid4(), buyer, "SELF", withdrawal_consent=True)
    assert repo.orders[oid].buyer_account_id == buyer


async def test_create_order_allows_anyone_for_all_rated_book():
    svc, _ = _svc_with_gate(rating="ALL")
    oid = await svc.create_order(uuid.uuid4(), uuid.uuid4(), "SELF", withdrawal_consent=True)
    assert oid is not None
