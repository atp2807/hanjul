"""potato API 스키마 (camelCase)."""
from uuid import UUID

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class _Camel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class LoginRequest(_Camel):
    email: str
    password: str


class TokenResponse(_Camel):
    token: str
    role_cd: str


class OperatorResponse(_Camel):
    model_config = ConfigDict(
        alias_generator=to_camel, populate_by_name=True, from_attributes=True
    )
    id: UUID
    email: str
    name: str
    role_cd: str
