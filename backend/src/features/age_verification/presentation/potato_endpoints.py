"""potato API — 성인인증(AGE18) 심사 큐. 신분증 원본은 심사 즉시 삭제(PII 보관 최소화).

사진 열람은 이 라우터의 /{request_id}/photo 하나뿐 — 공개 URL이 아니라 운영자 인증
(get_current_operator) + IP 화이트리스트(potato 공통 게이트, api.py의 _potato_guard)를
매 요청마다 통과해야 바이트를 돌려준다. 심사완료(원본 삭제) 후에는 404.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response

from src.features.age_verification.application.age_verification_service import (
    AgeVerificationService,
)
from src.features.age_verification.presentation.dependencies import get_age_verification_service
from src.features.age_verification.presentation.schemas import AgeVerificationRequestResponse
from src.features.potato.application.audit import AuditService
from src.features.potato.domain.models import OperatorPrincipal
from src.features.potato.presentation.dependencies import (
    client_ip,
    get_audit_service,
    get_current_operator,
)
from src.features.potato.presentation.schemas import ReasonRequest

router = APIRouter(prefix="/potato/age-verification", tags=["potato"])

_EXT_MEDIA_TYPE = {"jpg": "image/jpeg", "png": "image/png", "webp": "image/webp"}


@router.get("", response_model=list[AgeVerificationRequestResponse])
async def list_pending(
    status: str | None = "PENDING",
    _op: OperatorPrincipal = Depends(get_current_operator),
    svc: AgeVerificationService = Depends(get_age_verification_service),
) -> list[AgeVerificationRequestResponse]:
    return [AgeVerificationRequestResponse.model_validate(r) for r in await svc.list_pending(status)]


@router.get("/{request_id}/photo")
async def get_photo(
    request_id: UUID,
    _op: OperatorPrincipal = Depends(get_current_operator),
    svc: AgeVerificationService = Depends(get_age_verification_service),
) -> Response:
    """심사용 신분증 원본 조회 — RequestNotFound(404, 중앙 핸들러)면 미존재/이미 삭제됨."""
    data, ext = await svc.get_photo(request_id)
    return Response(content=data, media_type=_EXT_MEDIA_TYPE.get(ext, "application/octet-stream"))


@router.post("/{request_id}/approve", status_code=204)
async def approve(
    request_id: UUID,
    request: Request,
    op: OperatorPrincipal = Depends(get_current_operator),
    svc: AgeVerificationService = Depends(get_age_verification_service),
    audit: AuditService = Depends(get_audit_service),
) -> None:
    """승인 — verified_tier_cd=AGE18 갱신 + 원본 이미지 삭제. InvalidRequestState(409) → 중앙 핸들러."""
    await svc.approve(request_id, op.id)
    await audit.record(
        op.id, "AGE_VERIFICATION_APPROVE", "AGE_VERIFICATION_REQUEST", request_id, None, client_ip(request)
    )


@router.post("/{request_id}/reject", status_code=204)
async def reject(
    request_id: UUID,
    request: Request,
    body: ReasonRequest = ReasonRequest(),
    op: OperatorPrincipal = Depends(get_current_operator),
    svc: AgeVerificationService = Depends(get_age_verification_service),
    audit: AuditService = Depends(get_audit_service),
) -> None:
    """거부 — 원본 이미지 삭제. 사유는 감사로그에만 남김(요청 테이블엔 저장하지 않음)."""
    await svc.reject(request_id, op.id)
    await audit.record(
        op.id, "AGE_VERIFICATION_REJECT", "AGE_VERIFICATION_REQUEST", request_id,
        {"reason": body.reason}, client_ip(request),
    )
