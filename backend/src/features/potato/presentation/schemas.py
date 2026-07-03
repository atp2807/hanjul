"""potato API 스키마 (camelCase)."""
from datetime import datetime
from uuid import UUID

from pydantic import Field

from src.presentation.schema import CamelSchema


class LoginRequest(CamelSchema):
    email: str
    password: str


class TokenResponse(CamelSchema):
    token: str
    role: str


class OperatorResponse(CamelSchema):
    id: UUID
    email: str
    name: str
    role: str


# ── 모더레이션 ────────────────────────────────────────
class BookModerationItem(CamelSchema):
    id: UUID
    title: str
    author_id: UUID | None
    status: str
    blocked: bool
    blocked_at: datetime | None
    published_at: datetime | None


class TakedownRequest(CamelSchema):
    reason: str | None = Field(default=None, max_length=500)


# ── 신고 큐 ───────────────────────────────────────────
class ReportItem(CamelSchema):
    id: UUID
    reporter_id: UUID | None
    target_type: str
    target_id: UUID
    reason: str
    status: str
    created_at: datetime


class ResolveReportRequest(CamelSchema):
    action: str = Field(description="RESOLVE | DISMISS")
    resolution: str | None = Field(default=None, max_length=2000)


# ── 계정 조치 ─────────────────────────────────────────
class ReasonRequest(CamelSchema):
    reason: str | None = Field(default=None, max_length=500)


class AccountModerationView(CamelSchema):
    id: UUID
    email: str | None
    display_name: str | None
    role: str
    status: str
    review_blocked: bool
    review_blocked_at: datetime | None


# ── 대시보드 ──────────────────────────────────────────
class DashboardStats(CamelSchema):
    accounts: int
    books_total: int
    books_published: int
    books_blocked: int
    reports_open: int
