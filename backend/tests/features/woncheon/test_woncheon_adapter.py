"""WoncheonHttpAdapter 단위 — 미설정(api_key/base_url 없음) 시 명시적 실패.

⚠️ 실제 hanjul_woncheon 서버에 연결 시도하지 않는다 — 설정 검사가 httpx.AsyncClient
생성보다 먼저 일어나므로, 이 테스트는 네트워크를 전혀 만지지 않는다(설정 없으면 즉시 raise).
"""
import uuid

import pytest
from src.features.woncheon.domain.models import WoncheonNotConfigured
from src.features.woncheon.infrastructure.woncheon_adapter import (
    WoncheonHttpAdapter,
    build_woncheon_adapter,
)


async def test_raises_when_both_base_and_key_missing():
    adapter = WoncheonHttpAdapter(base_url="", api_key="")
    with pytest.raises(WoncheonNotConfigured):
        await adapter.report_payment(
            payout_id=uuid.uuid4(), gross_amount=1000, income_type_code="940906",
            payee_resident_number="9001011234567",
        )


async def test_raises_when_only_api_key_missing():
    adapter = WoncheonHttpAdapter(base_url="https://example.invalid", api_key="")
    with pytest.raises(WoncheonNotConfigured):
        await adapter.report_payment(
            payout_id=uuid.uuid4(), gross_amount=1000, income_type_code="940906",
            payee_resident_number="9001011234567",
        )


async def test_raises_when_only_base_missing():
    adapter = WoncheonHttpAdapter(base_url="", api_key="dummy-key")
    with pytest.raises(WoncheonNotConfigured):
        await adapter.report_payment(
            payout_id=uuid.uuid4(), gross_amount=1000, income_type_code="940906",
            payee_resident_number="9001011234567",
        )


def test_build_woncheon_adapter_reads_from_settings():
    class FakeSettings:
        WONCHEON_API_BASE = "https://example.invalid"
        WONCHEON_API_KEY = "k"

    adapter = build_woncheon_adapter(FakeSettings())
    assert adapter._base_url == "https://example.invalid"
    assert adapter._api_key == "k"
