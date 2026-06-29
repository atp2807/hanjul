"""운영자(potato) 전용 JWT — 고객 토큰과 **완전 분리**.

방화벽 2겹:
1. 별도 시크릿(POTATO_JWT_SECRET_KEY) — 고객 시크릿으로 서명된 토큰은 서명검증 실패.
2. aud="potato" — 고객 토큰(aud 없음)을 potato 검증에 넣으면 MissingRequiredClaim,
   반대로 potato 토큰(aud 있음)을 고객 검증(audience 미지정)에 넣으면 InvalidAudience.
"""
from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt

POTATO_AUDIENCE = "potato"


class PotatoTokenIssuer:
    def __init__(self, secret: str, alg: str = "HS256", ttl_hours: int = 12):
        self._secret = secret
        self._alg = alg
        self._ttl = timedelta(hours=ttl_hours)

    def issue(self, operator_id: UUID, role_cd: str) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "sub": str(operator_id),
            "role": role_cd,
            "aud": POTATO_AUDIENCE,
            "iat": now,
            "exp": now + self._ttl,
        }
        return jwt.encode(payload, self._secret, algorithm=self._alg)

    def verify(self, token: str) -> dict:
        return jwt.decode(
            token, self._secret, algorithms=[self._alg], audience=POTATO_AUDIENCE
        )
