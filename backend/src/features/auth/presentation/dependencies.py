"""auth 표현 레이어 DI 합성 루트."""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import get_session
from src.config.settings import settings
from src.features.auth.application.auth_service import AuthService
from src.features.auth.application.token import JwtTokenIssuer
from src.features.auth.infrastructure.account_repo import SqlAccountRepository
from src.features.auth.infrastructure.providers import build_providers


def get_auth_service(session: AsyncSession = Depends(get_session)) -> AuthService:
    return AuthService(
        repo=SqlAccountRepository(session),
        providers=build_providers(settings),
        token_issuer=JwtTokenIssuer(
            settings.JWT_SECRET_KEY, settings.JWT_ALG, settings.JWT_TTL_HOURS
        ),
    )
