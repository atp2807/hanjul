"""신고 서비스 — 접수(고객) + 목록/처리(운영자)."""
from datetime import UTC, datetime
from uuid import UUID

from src.features.reports.domain.models import (
    DISMISSED,
    OPEN,
    RESOLVED,
    TARGET_TYPES,
    InvalidTarget,
    Report,
    ReportNotFound,
    ReportRepository,
)


class ReportService:
    def __init__(self, repo: ReportRepository):
        self.repo = repo

    async def submit(
        self, reporter_id: UUID | None, target_type: str, target_id: UUID, reason: str
    ) -> Report:
        tt = (target_type or "").upper()
        if tt not in TARGET_TYPES:
            raise InvalidTarget(target_type)
        if not reason or not reason.strip():
            raise ValueError("reason required")
        return await self.repo.create(reporter_id, tt, target_id, reason.strip())

    async def list_open(
        self, status: str | None = OPEN, limit: int = 50, offset: int = 0
    ) -> list[Report]:
        return await self.repo.list_by_status(status, limit, offset)

    async def resolve(
        self,
        report_id: UUID,
        operator_id: UUID,
        action: str,
        resolution: str | None,
        now: datetime | None = None,
    ) -> str:
        """action: RESOLVE(조치완료) | DISMISS(기각). 처리된 status 반환."""
        act = (action or "").upper()
        if act not in ("RESOLVE", "DISMISS"):
            raise ValueError("action must be RESOLVE or DISMISS")
        report = await self.repo.get(report_id)
        if report is None:
            raise ReportNotFound()
        status = RESOLVED if act == "RESOLVE" else DISMISSED
        await self.repo.resolve(
            report_id, status, operator_id, resolution, now or datetime.now(UTC)
        )
        return status
