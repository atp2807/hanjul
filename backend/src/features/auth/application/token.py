"""JWT 세션 토큰 발급/검증."""
from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt


class JwtTokenIssuer:
    def __init__(self, secret: str, alg: str = "HS256", ttl_hours: int = 72):
        self._secret = secret
        self._alg = alg
        self._ttl = timedelta(hours=ttl_hours)

    def issue(self, account_id: UUID, role: str) -> str:
        now = datetime.now(UTC)
        payload = {"sub": str(account_id), "role": role, "iat": now, "exp": now + self._ttl}
        return jwt.encode(payload, self._secret, algorithm=self._alg)

    def verify(self, token: str) -> dict:
        return jwt.decode(token, self._secret, algorithms=[self._alg])
