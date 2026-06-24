"""토스 결제 게이트웨이 — PaymentGateway 포트 구현.

verify(paymentKey, amount, orderId) = 토스 /payments/confirm 승인.
성공(status DONE/금액 일치)이면 True, 토스 거절(PaymentError)이면 False.
PAYMENT_DEMO=False 일 때 주입.
"""
import logging

from src.features.billing.infrastructure.toss_client import PaymentError, TossPaymentsClient

logger = logging.getLogger("app")


class TossPaymentGateway:
    provider_cd = "TOSS"

    def __init__(self, secret_key: str, mock_mode: bool = False):
        self._client = TossPaymentsClient(secret_key, mock_mode)

    async def verify(self, pg_tx_id: str, expected_amount: int, order_ref: str | None = None) -> bool:
        if not order_ref:
            logger.warning("토스 승인에 orderId(order_ref) 누락")
            return False
        try:
            result = await self._client.confirm_payment(
                payment_key=pg_tx_id,
                order_id=order_ref,
                amount=expected_amount,
                idempotency_key=order_ref,  # 주문 1건당 고정 → timeout 재시도 시 중복 승인 차단
            )
        except PaymentError as e:
            logger.warning("토스 승인 거절 order=%s code=%s msg=%s", order_ref, e.code, e.message)
            return False
        # 토스는 confirm 200이면 승인 완료. 금액·상태 한 번 더 방어적 확인.
        return result.get("status") == "DONE" and int(result.get("totalAmount", 0)) == expected_amount
