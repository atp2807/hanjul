"""토스페이먼츠 결제 승인 클라이언트.

haedream(택스랩) 운영 코드 이식 — 단일 가맹점(샌드박스 테스트키)으로 정리.
핵심: POST /v1/payments/confirm {paymentKey, orderId, amount} + Basic auth(secret_key).
멱등키 헤더로 timeout 재시도 시 중복 결제 차단(토스 측 dedup).
"""
import base64
import json
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import httpx

logger = logging.getLogger("app")

TOSS_BASE_URL = "https://api.tosspayments.com/v1"
TOSS_API_TIMEOUT = 60.0  # 토스 권장: 결제 처리 60초


class PaymentError(Exception):
    """토스 결제 에러 — code/message 보존."""

    def __init__(self, code: str, message: str, details: dict | None = None):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)


class TossPaymentsClient:
    def __init__(self, secret_key: str, mock_mode: bool = False):
        self._secret_key = secret_key
        self._mock_mode = mock_mode

    def _auth_header(self) -> str:
        if not self._secret_key:
            return ""
        encoded = base64.b64encode(f"{self._secret_key}:".encode()).decode()
        return f"Basic {encoded}"

    def _is_mock(self, payment_key: str) -> bool:
        # 오직 서버 설정(mock_mode)만. payment_key 프리픽스로는 절대 mock 진입 금지 —
        # 클라가 'mock_*' 보내 실 승인 우회하는 무료결제 공격 차단.
        return self._mock_mode

    def _handle_error(self, response: httpx.Response) -> None:
        try:
            data = response.json()
            raise PaymentError(
                code=data.get("code", "UNKNOWN_ERROR"),
                message=data.get("message", "알 수 없는 오류"),
                details=data,
            )
        except json.JSONDecodeError:
            raise PaymentError(
                code="INVALID_RESPONSE",
                message="토스 응답 파싱 실패",
                details={"status_code": response.status_code, "body": response.text},
            )

    async def confirm_payment(
        self, payment_key: str, order_id: str, amount: int, idempotency_key: str | None = None
    ) -> dict[str, Any]:
        """결제 승인 — 위젯에서 받은 paymentKey + 우리 orderId + 금액을 토스가 검증·승인."""
        if self._is_mock(payment_key):
            logger.debug("[MOCK] toss confirm key=%s order=%s amt=%d", payment_key, order_id, amount)
            return self._mock_confirm(payment_key, order_id, amount)

        if not self._secret_key:
            raise PaymentError(code="CONFIG_ERROR", message="토스 시크릿키 미설정")

        headers = {"Authorization": self._auth_header(), "Content-Type": "application/json"}
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{TOSS_BASE_URL}/payments/confirm",
                    headers=headers,
                    json={"paymentKey": payment_key, "orderId": order_id, "amount": amount},
                    timeout=TOSS_API_TIMEOUT,
                )
                if response.status_code != 200:
                    self._handle_error(response)
                result = response.json()
                logger.info("토스 승인 완료 order=%s method=%s", order_id, result.get("method"))
                return result
        except PaymentError:
            raise
        except httpx.TimeoutException:
            raise PaymentError(code="TIMEOUT", message="토스 응답 시간 초과")
        except httpx.RequestError as e:
            raise PaymentError(code="NETWORK_ERROR", message="네트워크 오류", details={"error": str(e)})

    def _mock_confirm(self, payment_key: str, order_id: str, amount: int) -> dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        return {
            "paymentKey": payment_key,
            "orderId": order_id,
            "status": "DONE",
            "method": "카드",
            "totalAmount": amount,
            "approvedAt": now,
            "mock": True,
        }
