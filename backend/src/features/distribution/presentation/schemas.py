"""distribution API 스키마 (camelCase)."""
from datetime import datetime
from uuid import UUID

from src.presentation.schema import CamelSchema


class DistributeRequest(CamelSchema):
    channel: str  # KYOBO | YES24 | ALADIN ...


class DistributionResponse(CamelSchema):
    id: UUID
    book_id: UUID
    channel_cd: str
    status_cd: str
    message: str | None
    created_at: datetime
