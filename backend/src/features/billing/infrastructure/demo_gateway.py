"""데모 결제 게이트웨이 — 검증 없이 성공 처리 (개발/데모 전용).

settings.PAYMENT_DEMO=True 일 때만 주입. 운영(False)은 PortonePaymentGateway.
"""


class DemoPaymentGateway:
    provider_cd = "DEMO"

    async def verify(self, pg_tx_id: str, expected_amount: int) -> bool:
        return True
