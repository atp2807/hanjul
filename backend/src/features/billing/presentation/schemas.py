"""billing API 스키마 (camelCase)."""
from uuid import UUID

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class _Camel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)


class CreateOrderRequest(_Camel):
    book_id: UUID
    buyer_account_id: UUID
    amount: int
    channel: str = "SELF"  # SELF | EXTERNAL


class OrderResponse(_Camel):
    id: UUID
    book_id: UUID
    buyer_account_id: UUID
    amount_amt: int
    channel_cd: str
    status_cd: str


class ConfirmPaymentRequest(_Camel):
    pg_tx_id: str


class SettlementResponse(_Camel):
    channel_cd: str
    gross_amt: int
    platform_fee_amt: int
    withholding_amt: int
    payout_amt: int


class LibraryItemResponse(_Camel):
    book_id: UUID
    title: str
    kind: str
    price_amt: int | None
    cover_url: str | None
