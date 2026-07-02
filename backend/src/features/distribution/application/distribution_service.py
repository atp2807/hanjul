"""distribution 서비스 — 출간물(EPUB+ONIX)을 서점 채널로 전송하고 결과 기록."""
from uuid import UUID

from src.features.distribution.domain.models import (
    DistributionChannel,
    DistributionRepository,
    DistributionView,
)


class DistributionService:
    def __init__(self, repo: DistributionRepository, channel: DistributionChannel):
        self.repo = repo
        self.channel = channel

    async def distribute(
        self, book_id: UUID, epub: bytes, onix: str, filename: str
    ) -> DistributionView:
        """채널로 전송 시도 → 성공/실패를 항상 기록(감사추적). 실패해도 레코드는 남김."""
        try:
            await self.channel.deliver(str(book_id), epub, onix, filename)
            return await self.repo.record(book_id, self.channel.channel, "SENT", "")
        except Exception as e:  # 네트워크/인증 실패 등
            return await self.repo.record(book_id, self.channel.channel, "FAILED", str(e)[:500])

    async def history(self, book_id: UUID) -> list[DistributionView]:
        return await self.repo.list_for_book(book_id)
