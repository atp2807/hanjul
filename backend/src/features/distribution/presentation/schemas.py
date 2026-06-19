"""distribution API 스키마 (camelCase)."""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class _Camel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)


class DistributeRequest(_Camel):
    channel: str  # KYOBO | YES24 | ALADIN ...


class DistributionResponse(_Camel):
    id: UUID
    book_id: UUID
    channel_cd: str
    status_cd: str
    message: str | None
    created_at: datetime
