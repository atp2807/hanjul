"""도메인 예외 공통 베이스 — 프레임워크 무관(순수 Exception + status_code).

각 피처 도메인 예외가 상속하면, 표현층이 try/except로 HTTPException을 수동 매핑할 필요
없이 main.py의 단일 핸들러가 status_code + detail로 자동 변환한다.

status는 도메인이 소유(예외 종류가 곧 상태). 사용자용 메시지는 detail(한국어 가능).
인증/인가 등 표현층 고유 판단(예: 소유자 검증 403)은 표현층에서 HTTPException 유지 가능.
"""


class DomainError(Exception):
    """모든 도메인 예외의 베이스. status_code 로 HTTP 매핑."""
    status_code: int = 400
    default_detail: str = "요청을 처리할 수 없어요."

    def __init__(self, detail: str | None = None):
        self.detail = detail or self.default_detail
        super().__init__(self.detail)


class NotFoundError(DomainError):
    status_code = 404
    default_detail = "찾을 수 없어요."


class ConflictError(DomainError):
    status_code = 409
    default_detail = "현재 상태에서는 처리할 수 없어요."


class ValidationError(DomainError):
    status_code = 422
    default_detail = "입력을 확인해 주세요."


class ForbiddenError(DomainError):
    status_code = 403
    default_detail = "권한이 없어요."


class UnauthorizedError(DomainError):
    status_code = 401
    default_detail = "인증이 필요해요."


class PaymentError(DomainError):
    status_code = 402
    default_detail = "결제에 실패했어요."


class UpstreamError(DomainError):
    """외부 연동(PG·서점 등) 실패."""
    status_code = 502
    default_detail = "외부 서비스 처리에 실패했어요."
