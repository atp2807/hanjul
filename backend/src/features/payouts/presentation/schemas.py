"""payouts API 스키마 (camelCase)."""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class _Camel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)


class BankAccountRequest(_Camel):
    holder_name: str = Field(min_length=1, max_length=100)
    bank_cd: str = Field(min_length=1, max_length=20)
    account_no: str = Field(min_length=6, max_length=30)


class BankAccountResponse(_Camel):
    id: UUID
    holder_name: str
    bank_cd: str
    account_no_masked: str


class PayableResponse(_Camel):
    gross_amt: int
    withholding_amt: int
    net_amt: int
    order_count: int


class PayoutResponse(_Camel):
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
