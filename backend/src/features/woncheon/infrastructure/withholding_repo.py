"""WithholdingRepository 의 SQLAlchemy 구현 — bill.withholding_subject + bill.payout."""
import uuid
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.features.woncheon.domain.models import UnreportedPayoutView, WithholdingSubjectView
from src.infrastructure.db.models.payout import Payout
from src.infrastructure.db.models.withholding import WithholdingSubject


def _subject_view(row: WithholdingSubject) -> WithholdingSubjectView:
    return WithholdingSubjectView(
        payout_id=row.payout_id,
        resident_no_enc=row.resident_no_enc,
        income_type_code=row.income_type_code,
        created_at=row.created_at,
    )


class SqlWithholdingRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_subject(self, payout_id: UUID) -> WithholdingSubjectView | None:
        row = (
            await self.session.execute(
                select(WithholdingSubject).where(WithholdingSubject.payout_id == payout_id)
            )
        ).scalar_one_or_none()
        return _subject_view(row) if row else None

    async def upsert_subject(
        self, payout_id: UUID, resident_no_enc: str, income_type_code: str
    ) -> WithholdingSubjectView:
        row = (
            await self.session.execute(
                select(WithholdingSubject).where(WithholdingSubject.payout_id == payout_id)
            )
        ).scalar_one_or_none()
        if row is None:
            row = WithholdingSubject(
                id=uuid.uuid4(), payout_id=payout_id,
                resident_no_enc=resident_no_enc, income_type_code=income_type_code,
            )
            self.session.add(row)
        else:
            row.resident_no_enc = resident_no_enc
            row.income_type_code = income_type_code
        await self.session.commit()
        await self.session.refresh(row)
        return _subject_view(row)

    async def get_payout_gross(self, payout_id: UUID) -> int | None:
        p = await self.session.get(Payout, payout_id)
        return int(p.gross_amt) if p else None

    async def mark_reported(self, payout_id: UUID, when: datetime) -> None:
        p = await self.session.get(Payout, payout_id)
        if p is not None:
            p.woncheon_reported_at = when
            await self.session.commit()

    async def list_unreported_paid(self) -> list[UnreportedPayoutView]:
        rows = (
            await self.session.execute(
                select(Payout).where(Payout.status == "PAID", Payout.woncheon_reported_at.is_(None))
            )
        ).scalars().all()
        if not rows:
            return []
        ids_with_subject = set(
            (await self.session.execute(select(WithholdingSubject.payout_id))).scalars().all()
        )
        return [
            UnreportedPayoutView(
                payout_id=p.id, author_id=p.author_id,
                gross_amt=int(p.gross_amt), net_amt=int(p.net_amt),
                paid_at=p.paid_at, has_subject=p.id in ids_with_subject,
            )
            for p in rows
        ]
