"""age-verification API 스키마 (camelCase). id_photo_key는 절대 노출하지 않음(PII 키)."""
from datetime import datetime
from uuid import UUID

from src.presentation.schema import CamelSchema


class AgeVerificationRequestResponse(CamelSchema):
    id: UUID
    account_id: UUID
    status: str  # PENDING | APPROVED | REJECTED
    created_at: datetime
    reviewed_at: datetime | None = None
    reviewed_by: UUID | None = None
