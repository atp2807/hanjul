"""distribution 도메인 — 배포 결과 뷰 + 채널/레포 포트."""
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from src.shared.errors import DomainError


@dataclass
class DistributionView:
    id: UUID
    book_id: UUID
    channel: str
    status: str       # SENT | FAILED
    message: str | None
    created_at: datetime


class UnknownChannel(DomainError):
    """배포 채널 미설정/미지원 (400). 표현층 매핑 없이 중앙 핸들러가 처리."""
    status_code = 400

    def __init__(self, channel: str):
        self.channel = channel
        super().__init__("배포 채널을 찾을 수 없어요. (DISTRIBUTION_DEMO 또는 SFTP 설정이 필요해요.)")


class DistributionChannel(Protocol):
    """서점 배포 채널 — SFTP/API 등을 같은 계약으로. 실패 시 예외."""
    channel: str

    async def deliver(self, reference: str, epub: bytes, onix: str, filename: str) -> None:
        ...


class DistributionRepository(Protocol):
    async def record(self, book_id: UUID, channel: str, status: str, message: str) -> DistributionView:
        ...

    async def list_for_book(self, book_id: UUID) -> list[DistributionView]:
        ...
