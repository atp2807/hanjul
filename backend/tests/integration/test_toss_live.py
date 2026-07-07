"""토스 샌드박스 실호출 — 테스트키로 confirm 엔드포인트 실제 도달 검증.

opt-in: RUN_TOSS_LIVE=1 일 때만 (네트워크 + 실 키 필요). 평소 pytest는 스킵.
존재하지 않는 paymentKey로 confirm → 토스가 인증을 통과시킨 뒤 NOT_FOUND_PAYMENT 등
결제-레벨 에러로 거절 → 게이트웨이는 False. 이는 (키 유효 + 인증 헤더 + 엔드포인트 도달)을
실제로 입증한다. 401/CONFIG_ERROR(키 문제)면 실패.
"""
import os
import uuid

import pytest

from src.config.settings import settings
from src.features.billing.infrastructure.toss_client import PaymentError, TossPaymentsClient
from src.features.billing.infrastructure.toss_gateway import TossPaymentGateway

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(not os.getenv("RUN_TOSS_LIVE"), reason="RUN_TOSS_LIVE=1 일 때만 실 샌드박스 호출"),
]


async def test_sandbox_auth_reaches_confirm():
    """실 키로 confirm 호출 → 결제-레벨 거절(인증은 통과)."""
    client = TossPaymentsClient(settings.TOSS_TEST_SECRET_KEY, mock_mode=False)
    assert settings.TOSS_TEST_SECRET_KEY.startswith("test_sk_"), "샌드박스 시크릿키여야 함"
    with pytest.raises(PaymentError) as ei:
        await client.confirm_payment(
            payment_key=f"fake_{uuid.uuid4().hex}",
            order_id=str(uuid.uuid4()),
            amount=10000,
        )
    # 인증 실패(UNAUTHORIZED_KEY)나 CONFIG_ERROR가 아니라 '결제 없음/처리불가' 류여야 함
    assert ei.value.code not in ("CONFIG_ERROR", "UNAUTHORIZED_KEY", "INVALID_API_KEY"), ei.value.details


async def test_gateway_returns_false_on_real_rejection():
    gw = TossPaymentGateway(settings.TOSS_TEST_SECRET_KEY, mock_mode=False)
    ok = await gw.verify(f"fake_{uuid.uuid4().hex}", 10000, order_ref=str(uuid.uuid4()))
    assert ok is False
