"""인메모리 ReportRepository(reports 피처) — 서비스 단위 테스트용.

Protocol 구현 대상: src.features.reports.domain.models.ReportRepository
  (create · list_by_status · get · resolve)
"""
import uuid
from datetime import UTC, datetime
from uuid import UUID

from src.features.reports.domain.models import OPEN, Report


# ── Fake 리포지토리 ──────────────────────────────────
class FakeReportRepository:
    def __init__(self) -> None:
        self.reports: dict[UUID, Report] = {}

    def seed(self, report: Report) -> None:
        self.reports[report.id] = report

    async def create(self, reporter_id, target_type, target_id, reason) -> Report:
        report = Report(
            id=uuid.uuid4(), reporter_id=reporter_id, target_type=target_type, target_id=target_id,
            reason=reason, status=OPEN, resolution=None, resolved_by=None,
            created_at=datetime.now(UTC), resolved_at=None,
        )
        self.reports[report.id] = report
        return report

    async def list_by_status(self, status, limit, offset) -> list[Report]:
        rows = [r for r in self.reports.values() if status is None or r.status == status]
        rows.sort(key=lambda r: r.created_at, reverse=True)
        return rows[offset:offset + limit]

    async def get(self, report_id) -> Report | None:
        return self.reports.get(report_id)

    async def resolve(self, report_id, status, operator_id, resolution, now) -> None:
        r = self.reports.get(report_id)
        if r is not None:
            r.status = status
            r.resolved_by = operator_id
            r.resolution = resolution
            r.resolved_at = now
