"""대시보드 서비스 — 운영 현황 카운트."""
from typing import Protocol


class StatsRepository(Protocol):
    async def stats(self) -> dict: ...


class DashboardService:
    def __init__(self, repo: StatsRepository):
        self._repo = repo

    async def stats(self) -> dict:
        return await self._repo.stats()
