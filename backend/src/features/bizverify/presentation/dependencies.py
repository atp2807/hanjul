"""bizverify 표현 레이어 DI."""
from src.config.settings import settings
from src.features.bizverify.application.bizverify_service import BizVerifyService
from src.features.bizverify.infrastructure.nts_registry import NtsBusinessRegistry


def get_bizverify_service() -> BizVerifyService:
    return BizVerifyService(NtsBusinessRegistry(settings.NTS_BUSINESS_API_KEY))
