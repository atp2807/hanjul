"""woncheon HTTP 어댑터 — 실 테넌트 등록 전(lr-ac61f505)이라 미설정 시 명시적 실패.

계약(조사 완료, lr-ac61f505): POST {base}/api/v1/payments, X-API-Key 헤더,
Idempotency-Key=payout_id 로 멱등, body external_payment_id=payout_id.

httpx 직접 호출로 구현(공개 pip 패키지 `hanjul`(woncheon SDK) 의존 대신) — 이 레포 자체가
"hanjul"이라 이름 충돌 소지도 있고, 계약만 맞으면 SDK로 교체 가능하니 지금은 최소 의존.

⚠️ WONCHEON_API_BASE/WONCHEON_API_KEY 가 비어 있으면(현재 dev 기본값) 이 어댑터는 절대
실제 네트워크 연결을 시도하지 않는다 — httpx.AsyncClient 생성 전에 설정을 검사해 즉시
WoncheonNotConfigured 를 raise 한다(조용한 무동작 금지, 로그로도 명확히 남김).
"""
import logging
from uuid import UUID

import httpx

from src.features.woncheon.domain.models import ReportResult, WoncheonNotConfigured

logger = logging.getLogger(__name__)


class WoncheonHttpAdapter:
    """라이브 어댑터 — base_url/api_key 는 설정(settings.py)에서 나중 주입."""

    def __init__(self, base_url: str, api_key: str):
        self._base_url = base_url
        self._api_key = api_key

    async def report_payment(
        self, payout_id: UUID, gross_amount: int, income_type_code: str, payee_resident_number: str
    ) -> ReportResult:
        if not self._base_url or not self._api_key:
            logger.error(
                "woncheon 미설정 — WONCHEON_API_BASE/WONCHEON_API_KEY 없음 "
                "(테넌트 등록 전, lr-ac61f505). payout=%s 신고 불가.",
                payout_id,
            )
            raise WoncheonNotConfigured(
                "WONCHEON_API_BASE/WONCHEON_API_KEY 미설정 — woncheon 테넌트 등록 전이라 실 신고 불가"
            )
        async with httpx.AsyncClient(base_url=self._base_url, timeout=30) as client:
            res = await client.post(
                "/api/v1/payments",
                headers={"X-API-Key": self._api_key, "Idempotency-Key": str(payout_id)},
                json={
                    "external_payment_id": str(payout_id),
                    "gross_amount": gross_amount,
                    "income_type_code": income_type_code,
                    "payee": {"resident_number": payee_resident_number},
                },
            )
            res.raise_for_status()
            data = res.json()
            return ReportResult(ok=True, external_reference=data.get("id"))


def build_woncheon_adapter(settings) -> WoncheonHttpAdapter:
    return WoncheonHttpAdapter(settings.WONCHEON_API_BASE, settings.WONCHEON_API_KEY)
