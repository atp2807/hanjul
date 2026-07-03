"""auth API 스키마 (camelCase)."""
from uuid import UUID

from src.presentation.schema import CamelSchema


class LoginUrlResponse(CamelSchema):
    authorization_url: str


class AccountResponse(CamelSchema):
    id: UUID
    email: str | None
    display_name: str | None
    role: str
    bio: str | None = None


class AuthTokenResponse(CamelSchema):
    token: str
    is_new: bool
    account: AccountResponse
