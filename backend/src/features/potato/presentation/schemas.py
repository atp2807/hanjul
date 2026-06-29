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


# ── 신고 큐 ───────────────────────────────────────────
class ReportItem(_Camel):
    id: UUID
    reporter_id: UUID | None
    target_type: str
    target_id: UUID
    reason: str
    status: str
    created_at: datetime


class ResolveReportRequest(_Camel):
    action: str = Field(description="RESOLVE | DISMISS")
    resolution: str | None = Field(default=None, max_length=2000)


# ── 계정 조치 ─────────────────────────────────────────
class ReasonRequest(_Camel):
    reason: str | None = Field(default=None, max_length=500)


class AccountModerationView(_Camel):
    id: UUID
    email: str | None
    display_name: str | None
    role_cd: str
    status_cd: str
    review_blocked: bool
    review_blocked_at: datetime | None


# ── 대시보드 ──────────────────────────────────────────
class DashboardStats(_Camel):
    accounts: int
    books_total: int
    books_published: int
    books_blocked: int
    reports_open: int
