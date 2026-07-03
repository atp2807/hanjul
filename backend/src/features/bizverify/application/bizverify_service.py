"""bizverify 서비스 — 체크섬 검증 + 국세청 조회 오케스트레이션."""
from src.engine.validation.business_number import is_valid_business_number
from src.features.bizverify.domain.models import (
    BusinessNotRegistered,
    BusinessRegistration,
    BusinessRegistryPort,
    InvalidBusinessNumber,
)


class BizVerifyService:
    def __init__(self, registry: BusinessRegistryPort):
        self.registry = registry

    async def verify(self, business_no: str) -> BusinessRegistration:
        """형식(체크섬) 먼저 검증 후 국세청 조회. 폐업/휴업도 정상 결과(is_active=False)로 반환."""
        if not is_valid_business_number(business_no):
            raise InvalidBusinessNumber()
        result = await self.registry.lookup(business_no)
        if result is None:
            raise BusinessNotRegistered()
        return result
