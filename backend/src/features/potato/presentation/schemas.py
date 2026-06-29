"""potato API 스키마 (camelCase)."""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
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


# ── 모더레이션 ────────────────────────────────────────
class BookModerationItem(_Camel):
    id: UUID
    title: str
    author_id: UUID | None
    status: str
    blocked: bool
    blocked_at: datetime | None
    published_at: datetime | None


class TakedownRequest(_Camel):
    reason: str | None = Field(default=None, max_length=500)
