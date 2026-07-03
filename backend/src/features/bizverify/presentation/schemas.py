"""bizverify API 스키마 (camelCase)."""
from src.presentation.schema import CamelSchema


class BusinessRegistrationResponse(CamelSchema):
    business_no: str
    name: str | None
    ceo_name: str | None
    status: str
    status_name: str
    is_active: bool
