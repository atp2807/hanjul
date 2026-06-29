"""운영자 인증 서비스 — 이메일+비밀번호 로그인 → potato JWT."""
from uuid import UUID

from src.features.potato.application.password import verify_password
from src.features.potato.application.token import PotatoTokenIssuer
from src.features.potato.domain.models import (
    InvalidCredentials,
    Operator,
    OperatorInactive,
    OperatorNotFound,
    OperatorRepository,
)


class PotatoAuthService:
    def __init__(self, repo: OperatorRepository, token_issuer: PotatoTokenIssuer):
        self._repo = repo
        self._token = token_issuer

    async def login(self, email: str, password: str) -> tuple[str, str]:
        """성공 시 (token, role_cd). 자격증명 먼저 검증(비활성 여부를 오답에 노출 안 함)."""
        operator = await self._repo.get_by_email(email)
        if operator is None or not operator.password_hash or not verify_password(
            password, operator.password_hash
        ):
            raise InvalidCredentials()
        if not operator.is_active:
            raise OperatorInactive()
        return self._token.issue(operator.id, operator.role_cd), operator.role_cd

    async def get_operator(self, operator_id: UUID) -> Operator:
        operator = await self._repo.get(operator_id)
        if operator is None:
            raise OperatorNotFound()
        return operator
