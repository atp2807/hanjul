"""대시보드 집계 — 읽기전용 카운트(여러 스키마 횡단).

대시보드는 본질상 횡단 read-model 이라 ORM 모델을 직접 집계(읽기전용, 변경 없음).
운영 데이터 변경은 각 피처 서비스가 담당 — 여기는 카운트만.
"""
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.db.models.account import Account
from src.infrastructure.db.models.book import Book
from src.infrastructure.db.models.report import Report


class SqlStatsRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def _count(self, stmt) -> int:
        return (await self.session.execute(stmt)).scalar_one()

    async def stats(self) -> dict:
        return {
            "accounts": await self._count(select(func.count()).select_from(Account)),
            "books_total": await self._count(select(func.count()).select_from(Book)),
            "books_published": await self._count(
                select(func.count())
                .select_from(Book)
                .where(Book.status == "PUBLISHED", Book.blocked_at.is_(None))
            ),
            "books_blocked": await self._count(
                select(func.count()).select_from(Book).where(Book.blocked_at.isnot(None))
            ),
            "reports_open": await self._count(
                select(func.count()).select_from(Report).where(Report.status == "OPEN")
            ),
        }
