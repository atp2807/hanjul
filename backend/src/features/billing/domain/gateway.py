"""결제대행(PG) 포트 — 포트원/토스 등을 같은 계약으로."""
from typing import Protocol


class PaymentGateway(Protocol):
    provider_cd: str

    async def verify(self, pg_tx_id: str, expected_amount: int) -> bool:
        """PG 서버에 실제 결제를 조회해 금액 일치를 검증."""
        ...
