"""DistributionRepository 의 SQLAlchemy 구현."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.features.distribution.domain.models import DistributionView
from src.infrastructure.db.models.distribution import Distribution


def _to_view(d: Distribution) -> DistributionView:
    return DistributionView(
        id=d.id, book_id=d.book_id, channel=d.channel,
        status=d.status, message=d.message, created_at=d.created_at,
    )


class SqlDistributionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def record(self, book_id, channel, status, message) -> DistributionView:
        d = Distribution(book_id=book_id, channel=channel, status=status, message=message or None)
        self.session.add(d)
        await self.session.flush()
        await self.session.commit()
        return _to_view(d)

    async def list_for_book(self, book_id) -> list[DistributionView]:
        stmt = select(Distribution).where(Distribution.book_id == book_id).order_by(Distribution.created_at.desc())
        rows = (await self.session.execute(stmt)).scalars().all()
        return [_to_view(d) for d in rows]
