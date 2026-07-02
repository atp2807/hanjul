"""reports API 스키마 (고객 접수)."""
from uuid import UUID

from pydantic import Field

from src.presentation.schema import CamelSchema


class SubmitReportRequest(CamelSchema):
    target_type: str = Field(description="BOOK | REVIEW | ACCOUNT")
    target_id: UUID
    reason: str = Field(min_length=1, max_length=2000)


class SubmitReportResponse(CamelSchema):
    id: UUID
