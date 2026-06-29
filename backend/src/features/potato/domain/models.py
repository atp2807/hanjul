"""potato 도메인 — 운영자(내부 직원) 값객체 + 에러 + 포트.

운영자는 고객(usr.account)과 완전히 분리된 신원 영역. 소셜가입·구매 불가.
role_cd: OPERATOR(신뢰·안전 운영) | DEVELOPER(+ 시스템/엔진 메뉴). DEVELOPER ⊇ OPERATOR.
"""
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

OPERATOR = "OPERATOR"
DEVELOPER = "DEVELOPER"
ROLES = {OPERATOR, DEVELOPER}


@dataclass
class Operator:
    id: UUID
    email: str
    name: str
    role_cd: str
    is_active: bool
    password_hash: str | None = None


@dataclass(frozen=True)
class OperatorPrincipal:
    """potato JWT 클레임에서 복원한 운영자 주체 (DB 조회 없이 authz용)."""
    id: UUID
    role_cd: str

    @property
    def is_developer(self) -> bool:
        return self.role_cd == DEVELOPER


class OperatorNotFound(Exception):
    ...


class InvalidCredentials(Exception):
    """이메일 없음 또는 비밀번호 불일치 — 어느 쪽인지 드러내지 않음(401)."""


class OperatorInactive(Exception):
    """비활성화된 운영자 (403)."""


class OperatorRepository(Protocol):
    async def get_by_email(self, email: str) -> Operator | None: ...
    async def get(self, operator_id: UUID) -> Operator | None: ...
    async def create(
        self, email: str, name: str, role_cd: str, password_hash: str
    ) -> Operator: ...
