"""reports 도메인 — 신고 값객체 + 상태/대상 + 포트.

reporter(고객)가 접수, operator(운영자)가 처리. 두 영역을 잇는 경계 도메인.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

OPEN = "OPEN"
RESOLVED = "RESOLVED"
DISMISSED = "DISMISSED"

TARGET_TYPES = {"BOOK", "REVIEW", "ACCOUNT"}


@dataclass
class Report:
    id: UUID
    reporter_id: UUID | None
    target_type: str
    target_id: UUID
    reason: str
    status: str
    resolution: str | None
    resolved_by: UUID | None
    created_at: datetime
    resolved_at: datetime | None


class ReportNotFound(Exception):
    ...


class InvalidTarget(Exception):
    def __init__(self, target_type: str):
        super().__init__(f"invalid target type: {target_type}")


class ReportRepository(Protocol):
    async def create(
        self, reporter_id: UUID | None, target_type: str, target_id: UUID, reason: str
    ) -> Report: ...

    async def list_by_status(
        self, status: str | None, limit: int, offset: int
    ) -> list[Report]: ...

    async def get(self, report_id: UUID) -> Report | None: ...

    async def resolve(
        self, report_id: UUID, status: str, operator_id: UUID, resolution: str | None, now: datetime
    ) -> None: ...
