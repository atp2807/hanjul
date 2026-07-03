"""BizVerifyService — 체크섬 검증 + 국세청 조회 오케스트레이션."""
import pytest
from src.features.bizverify.application.bizverify_service import BizVerifyService
from src.features.bizverify.domain.models import (
    BusinessNotRegistered,
    BusinessRegistration,
    InvalidBusinessNumber,
)

from tests.fixtures.fake_business_registry import FakeBusinessRegistry

VALID_NO = "2208162517"


async def test_invalid_checksum_raises_before_lookup():
    svc = BizVerifyService(FakeBusinessRegistry(result=None))
    with pytest.raises(InvalidBusinessNumber):
        await svc.verify("2208162516")  # 체크섬 불일치


async def test_valid_but_not_registered_raises_not_found():
    svc = BizVerifyService(FakeBusinessRegistry(result=None))
    with pytest.raises(BusinessNotRegistered):
        await svc.verify(VALID_NO)


async def test_valid_and_registered_returns_registration():
    reg = BusinessRegistration(
        business_no=VALID_NO,
        name="포테이토크래프트",
        ceo_name="홍길동",
        status="01",
        status_name="계속사업자",
        is_active=True,
    )
    svc = BizVerifyService(FakeBusinessRegistry(result=reg))
    out = await svc.verify("220-81-62517")  # 하이픈 포함도 통과
    assert out is reg
    assert out.is_active is True
