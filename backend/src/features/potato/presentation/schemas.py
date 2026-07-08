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


# ── 사후 검토 큐 ──────────────────────────────────────
class ReviewQueueItem(CamelSchema):
    """운영자 주의가 필요한 책 — AGE18 발행책 + OPEN 신고책(조회 전용, 조치는 takedown 재사용)."""
    book_id: UUID
    title: str
    author_id: UUID | None
    rating: str
    reasons: list[str] = Field(description="AGE18 | REPORTED (복수 가능)")
    published_at: datetime | None


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


# ── woncheon 원천징수 신고 커넥터(lr-ac61f505) ───────────
class WithholdingSubjectRequest(CamelSchema):
    """지급 시점 원천징수 대상자 최소수집 — bank_account(계좌등록)와 별개."""
    resident_number: str
    income_type_code: str | None = Field(
        default=None, description="미지정 시 WONCHEON_DEFAULT_INCOME_TYPE_CODE 사용"
    )


class UnreportedWoncheonPayout(CamelSchema):
    payout_id: UUID
    author_id: UUID
    gross_amt: int
    net_amt: int
    paid_at: datetime
    has_subject: bool


# ── 주문/환불(potato Phase 2) ─────────────────────────
class OrderOpsItem(CamelSchema):
    """운영자 주문 목록 항목 — 구매자 제약 없이 최근 주문(환불 대상 탐색용)."""
    id: UUID
    book_id: UUID
    book_title: str
    buyer_account_id: UUID
    amount_amt: int
    channel: str
    status: str
    created_at: datetime
    paid_at: datetime | None


class RefundOrderRequest(CamelSchema):
    reason: str | None = Field(default=None, max_length=500)


# ── 대시보드 ──────────────────────────────────────────
class DashboardStats(CamelSchema):
    accounts: int
    books_total: int
    books_published: int
    books_blocked: int
    reports_open: int
