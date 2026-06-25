"""데모 결제 게이트웨이 — 검증 없이 성공 처리 (개발/데모 전용).

settings.PAYMENT_DEMO=True 일 때만 주입. 운영(False)은 TossPaymentGateway.
"""


class DemoPaymentGateway:
    provider_cd = "DEMO"

    async def verify(self, pg_tx_id: str, expected_amount: int, order_ref: str | None = None) -> bool:
        return True

    async def refund(self, pg_tx_id: str, reason: str, order_ref: str | None = None) -> bool:
        return True

    async def lookup_status(self, pg_tx_id: str) -> str | None:
        return None  # 데모는 실 PG 없음 → reconcile 불가
