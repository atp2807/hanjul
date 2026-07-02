"""payouts API 스키마 (camelCase)."""
from datetime import datetime
from uuid import UUID

from pydantic import Field

from src.presentation.schema import CamelSchema


class BankAccountRequest(CamelSchema):
    holder_name: str = Field(min_length=1, max_length=100)
    bank_cd: str = Field(min_length=1, max_length=20)
    account_no: str = Field(min_length=6, max_length=30)


class BankAccountResponse(CamelSchema):
    id: UUID
    holder_name: str
    bank_cd: str
    account_no_masked: str


class PayableResponse(CamelSchema):
    gross_amt: int
    withholding_amt: int
    net_amt: int
    order_count: int


class PayoutResponse(CamelSchema):
    id: UUID
    status_cd: str
    gross_amt: int
    withholding_amt: int
    net_amt: int
    holder_name: str | None
    bank_cd: str | None
    account_no_masked: str | None
    requested_at: datetime
    approved_at: datetime | None = None
    paid_at: datetime | None = None
    memo: str | None = None
