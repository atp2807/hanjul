"""auth API 스키마 (camelCase)."""
from uuid import UUID

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class _Camel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)


class LoginUrlResponse(_Camel):
    authorization_url: str


class AccountResponse(_Camel):
    id: UUID
    email: str | None
    display_name: str | None
    role_cd: str


class AuthTokenResponse(_Camel):
    token: str
    is_new: bool
    account: AccountResponse
