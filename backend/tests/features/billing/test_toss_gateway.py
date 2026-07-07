"""TossPaymentGateway 단위 — confirm 응답 매핑(네트워크 없음)."""

from src.features.billing.infrastructure.toss_client import PaymentError
from src.features.billing.infrastructure.toss_gateway import TossPaymentGateway


async def test_mock_confirm_success_returns_true():
    gw = TossPaymentGateway(secret_key="test_sk_x", mock_mode=True)
    assert await gw.verify("pk_abc", 10000, order_ref="order-1") is True


async def test_missing_order_ref_returns_false():
    gw = TossPaymentGateway(secret_key="test_sk_x", mock_mode=True)
    assert await gw.verify("pk_abc", 10000, order_ref=None) is False


async def test_amount_mismatch_returns_false(monkeypatch):
    gw = TossPaymentGateway(secret_key="test_sk_x")
    async def _confirm(**kw):
        return {"status": "DONE", "totalAmount": 9999}
    monkeypatch.setattr(gw._client, "confirm_payment", _confirm)
    assert await gw.verify("pk", 10000, order_ref="o1") is False


async def test_toss_rejection_returns_false(monkeypatch):
    gw = TossPaymentGateway(secret_key="test_sk_x")
    async def _confirm(**kw):
        raise PaymentError(code="NOT_FOUND_PAYMENT", message="결제 없음")
    monkeypatch.setattr(gw._client, "confirm_payment", _confirm)
    assert await gw.verify("pk", 10000, order_ref="o1") is False


async def test_provider_cd_is_toss():
    assert TossPaymentGateway(secret_key="x").provider_cd == "TOSS"


async def test_mock_refund_returns_true():
    gw = TossPaymentGateway(secret_key="test_sk_x", mock_mode=True)
    assert await gw.refund("pk", "변심", order_ref="o1") is True


async def test_refund_toss_rejection_returns_false(monkeypatch):
    gw = TossPaymentGateway(secret_key="test_sk_x")
    async def _cancel(**kw):
        raise PaymentError(code="ALREADY_CANCELED_PAYMENT", message="이미 취소")
    monkeypatch.setattr(gw._client, "cancel_payment", _cancel)
    assert await gw.refund("pk", "x", order_ref="o1") is False


async def test_refund_status_canceled_returns_true(monkeypatch):
    gw = TossPaymentGateway(secret_key="test_sk_x")
    async def _cancel(**kw):
        return {"status": "CANCELED"}
    monkeypatch.setattr(gw._client, "cancel_payment", _cancel)
    assert await gw.refund("pk", "x", order_ref="o1") is True


async def test_lookup_status_returns_toss_status(monkeypatch):
    gw = TossPaymentGateway(secret_key="test_sk_x")
    async def _get(pk):
        return {"status": "CANCELED"}
    monkeypatch.setattr(gw._client, "get_payment", _get)
    assert await gw.lookup_status("pk") == "CANCELED"


async def test_lookup_status_none_on_error(monkeypatch):
    gw = TossPaymentGateway(secret_key="test_sk_x")
    async def _get(pk):
        raise PaymentError(code="NOT_FOUND", message="없음")
    monkeypatch.setattr(gw._client, "get_payment", _get)
    assert await gw.lookup_status("pk") is None


def test_mock_prefix_does_not_bypass_real_confirm():
    """클라가 'mock_*' paymentKey 보내도 실 승인 우회 금지 (무료결제 공격 차단)."""
    from src.features.billing.infrastructure.toss_client import TossPaymentsClient

    live = TossPaymentsClient("test_sk_x", mock_mode=False)
    assert live._is_mock("mock_evil") is False  # 프리픽스로 mock 진입 불가
    mock = TossPaymentsClient("test_sk_x", mock_mode=True)
    assert mock._is_mock("anything") is True  # 서버 설정으로만 mock
