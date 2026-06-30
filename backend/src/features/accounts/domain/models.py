"""accounts 도메인 — 유저(사람) 프로필 + 리포지토리 포트.

usr.account = 사람(작가·독자). 인증(credential/token)은 auth 피처가 담당하고,
여기는 '유저' 도메인 = 프로필(이름·소개·역할) 조회/수정 + 이름 디렉토리(타 피처용).
"""
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass
class AccountProfile:
    id: UUID
    email: str | None
    display_name: str | None
    role_cd: str
    bio: str | None
    status_cd: str = "ACTIVE"  # ACTIVE | SUSPENDED (운영자 정지)
    # 서평단 자격회수는 더 이상 여기 없음 — commu.reviewer_block (campaigns 소유)


class AccountNotFound(Exception):
    def __init__(self, account_id: UUID):
        super().__init__(f"account not found: {account_id}")


class AccountRepository(Protocol):
    async def get(self, account_id: UUID) -> AccountProfile | None:
        ...

    async def exists(self, account_id: UUID) -> bool:
        ...

    async def update_bio(self, account_id: UUID, bio: str | None) -> None:
        ...

    async def names_for(self, account_ids: list[UUID]) -> dict[UUID, str | None]:
        """여러 계정의 표시이름 일괄 조회 — 타 피처가 이름 붙일 때(직접 JOIN 대체)."""
        ...

    async def set_status(self, account_id: UUID, status: str) -> None:
        """운영자 계정 정지/해제 (ACTIVE | SUSPENDED)."""
        ...
