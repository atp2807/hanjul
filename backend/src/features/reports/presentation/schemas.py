"""reports API 스키마 (고객 접수)."""
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class _Camel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class SubmitReportRequest(_Camel):
    target_type: str = Field(description="BOOK | REVIEW | ACCOUNT")
    target_id: UUID
    reason: str = Field(min_length=1, max_length=2000)


class SubmitReportResponse(_Camel):
    id: UUID
