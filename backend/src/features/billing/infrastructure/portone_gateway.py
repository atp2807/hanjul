"""포트원(PortOne) 결제 검증 어댑터.

주의: 라이브 검증은 PORTONE_API_SECRET 필요 → 운영 환경. 구조/플로우는 PaymentGateway 계약.
"""
import httpx

_PAYMENT_URL = "https://api.portone.io/payments/{payment_id}"


class PortonePaymentGateway:
    provider_cd = "PORTONE"

    def __init__(self, api_secret: str):
        self._api_secret = api_secret

    async def verify(self, pg_tx_id: str, expected_amount: int, order_ref: str | None = None) -> bool:
        async with httpx.AsyncClient(timeout=10) as client:
            res = await client.get(
                _PAYMENT_URL.format(payment_id=pg_tx_id),
                headers={"Authorization": f"PortOne {self._api_secret}"},
            )
            res.raise_for_status()
            data = res.json()
        return data.get("status") == "PAID" and int(data["amount"]["total"]) == expected_amount

    async def refund(self, pg_tx_id: str, reason: str, order_ref: str | None = None) -> bool:
        # 포트원 취소 미구현 — 현재 운영 PG는 토스. 필요 시 /payments/{id}/cancel 연동.
        raise NotImplementedError("PortOne refund 미구현")
