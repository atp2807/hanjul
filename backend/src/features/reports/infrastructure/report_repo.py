"""commu.report SQL 어댑터."""
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.features.reports.domain.models import Report
from src.infrastructure.db.models.report import Report as ReportRow


def _to_domain(r: ReportRow) -> Report:
    return Report(
        id=r.id,
        reporter_id=r.reporter_id,
        target_type=r.target_type,
        target_id=r.target_id,
        reason=r.reason,
        status=r.status,
        resolution=r.resolution,
        resolved_by=r.resolved_by,
        created_at=r.created_at,
        resolved_at=r.resolved_at,
    )


class SqlReportRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self, reporter_id: UUID | None, target_type: str, target_id: UUID, reason: str
    ) -> Report:
        row = ReportRow(
            id=uuid4(),
            reporter_id=reporter_id,
            target_type=target_type,
            target_id=target_id,
            reason=reason,
            status="OPEN",
        )
        self.session.add(row)
        await self.session.commit()
        await self.session.refresh(row)
        return _to_domain(row)

    async def list_by_status(
        self, status: str | None, limit: int, offset: int
    ) -> list[Report]:
        stmt = select(ReportRow)
        if status:
            stmt = stmt.where(ReportRow.status == status)
        stmt = stmt.order_by(ReportRow.created_at.desc()).limit(limit).offset(offset)
        rows = (await self.session.execute(stmt)).scalars().all()
        return [_to_domain(r) for r in rows]

    async def get(self, report_id: UUID) -> Report | None:
        row = await self.session.get(ReportRow, report_id)
        return _to_domain(row) if row else None

    async def resolve(
        self, report_id: UUID, status: str, operator_id: UUID, resolution: str | None, now: datetime
    ) -> None:
        row = await self.session.get(ReportRow, report_id)
        row.status = status
        row.resolved_by = operator_id
        row.resolution = resolution
        row.resolved_at = now
        await self.session.commit()

    async def list_open_target_ids(self, target_type: str) -> list[UUID]:
        """OPEN 신고가 달린 대상 id 목록(중복 제거) — 사후검토 큐(potato review-queue)용."""
        stmt = (
            select(ReportRow.target_id)
            .where(ReportRow.target_type == target_type, ReportRow.status == "OPEN")
            .distinct()
        )
        rows = (await self.session.execute(stmt)).scalars().all()
        return list(rows)
