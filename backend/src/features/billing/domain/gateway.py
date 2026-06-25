"""결제대행(PG) 포트 — 포트원/토스 등을 같은 계약으로."""
from typing import Protocol


class PaymentGateway(Protocol):
    provider_cd: str

    async def verify(self, pg_tx_id: str, expected_amount: int, order_ref: str | None = None) -> bool:
        """PG 서버에 실제 결제를 검증/승인. order_ref = 주문 식별자(토스 orderId 등)."""
        ...

    async def refund(self, pg_tx_id: str, reason: str, order_ref: str | None = None) -> bool:
        """결제 전체 취소(환불). 성공 시 True."""
        ...
