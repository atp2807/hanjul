"""distribution 도메인 — 배포 결과 뷰 + 채널/레포 포트."""
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID


@dataclass
class DistributionView:
    id: UUID
    book_id: UUID
    channel_cd: str
    status_cd: str       # SENT | FAILED
    message: str | None
    created_at: datetime


class UnknownChannel(Exception):
    def __init__(self, channel_cd: str):
        super().__init__(f"unknown distribution channel: {channel_cd}")


class DistributionChannel(Protocol):
    """서점 배포 채널 — SFTP/API 등을 같은 계약으로. 실패 시 예외."""
    channel_cd: str

    async def deliver(self, reference: str, epub: bytes, onix: str, filename: str) -> None:
        ...


class DistributionRepository(Protocol):
    async def record(self, book_id: UUID, channel_cd: str, status_cd: str, message: str) -> DistributionView:
        ...

    async def list_for_book(self, book_id: UUID) -> list[DistributionView]:
        ...
