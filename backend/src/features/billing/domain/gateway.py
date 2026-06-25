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

    async def lookup_status(self, pg_tx_id: str) -> str | None:
        """PG에서 결제 상태 재조회(웹훅 reconcile용). 예: DONE/CANCELED. 불가 시 None."""
        ...
