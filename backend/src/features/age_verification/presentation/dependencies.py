"""age_verification 표현 레이어 DI. 신분증 사진은 비공개 로컬 저장(AGE_VERIFICATION_DIR)."""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import get_session
from src.config.settings import settings
from src.features.accounts.application.account_service import AccountService
from src.features.accounts.infrastructure.account_repo import SqlAccountRepository
from src.features.age_verification.application.age_verification_service import (
    AgeVerificationService,
)
from src.features.age_verification.infrastructure.age_verification_repo import (
    SqlAgeVerificationRepository,
)
from src.features.age_verification.infrastructure.id_photo_storage import LocalDiskIdPhotoStorage


def get_age_verification_service(
    session: AsyncSession = Depends(get_session),
) -> AgeVerificationService:
    return AgeVerificationService(
        repo=SqlAgeVerificationRepository(session),
        storage=LocalDiskIdPhotoStorage(settings.AGE_VERIFICATION_DIR),
        account_tier=AccountService(SqlAccountRepository(session)),
    )
