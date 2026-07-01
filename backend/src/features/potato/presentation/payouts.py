"""potato API — 출금 관리 (승인·지급완료·반려). 실이체는 운영자 수동 + 감사."""
from uuid import UUID

from fastapi import APIRouter, Depends, Request

from src.features.payouts.application.payout_service import PayoutService
from src.features.payouts.presentation.dependencies import get_payout_service
from src.features.payouts.presentation.schemas import PayoutResponse
from src.features.potato.application.audit import AuditService
from src.features.potato.domain.models import OperatorPrincipal
from src.features.potato.presentation.dependencies import (
    client_ip,
    get_audit_service,
    get_current_operator,
)
from src.features.potato.presentation.schemas import ReasonRequest

router = APIRouter(prefix="/potato", tags=["potato"])



@router.get("/payouts", response_model=list[PayoutResponse])
async def list_payouts(
    status: str | None = "REQUESTED",
    _op: OperatorPrincipal = Depends(get_current_operator),
    svc: PayoutService = Depends(get_payout_service),
) -> list[PayoutResponse]:
    return [PayoutResponse.model_validate(p) for p in await svc.list_for_ops(status)]


async def _transition(request, op, audit, coro, action, payout_id, memo=None):
    # 도메인 예외(PayoutNotFound 404·InvalidPayoutState 409)는 중앙 핸들러가 매핑.
    # 예외 시 여기서 반환되므로 audit는 정상 전이(성공)에서만 기록된다(기존 동작 유지).
    await coro
    await audit.record(op.id, action, "PAYOUT", payout_id, {"memo": memo}, client_ip(request))


@router.post("/payouts/{payout_id}/approve", status_code=204)
async def approve(
    payout_id: UUID,
    request: Request,
    op: OperatorPrincipal = Depends(get_current_operator),
    svc: PayoutService = Depends(get_payout_service),
    audit: AuditService = Depends(get_audit_service),
) -> None:
    await _transition(request, op, audit, svc.approve(payout_id, op.id), "PAYOUT_APPROVE", payout_id)


@router.post("/payouts/{payout_id}/pay", status_code=204)
async def mark_paid(
    payout_id: UUID,
    request: Request,
    body: ReasonRequest = ReasonRequest(),
    op: OperatorPrincipal = Depends(get_current_operator),
    svc: PayoutService = Depends(get_payout_service),
    audit: AuditService = Depends(get_audit_service),
) -> None:
    """실이체 완료 후 지급확정 (이체는 운영자가 은행에서 수동 처리)."""
    await _transition(
        request, op, audit, svc.mark_paid(payout_id, op.id, body.reason), "PAYOUT_PAID", payout_id, body.reason
    )


@router.post("/payouts/{payout_id}/reject", status_code=204)
async def reject(
    payout_id: UUID,
    request: Request,
    body: ReasonRequest = ReasonRequest(),
    op: OperatorPrincipal = Depends(get_current_operator),
    svc: PayoutService = Depends(get_payout_service),
    audit: AuditService = Depends(get_audit_service),
) -> None:
    await _transition(
        request, op, audit, svc.reject(payout_id, op.id, body.reason), "PAYOUT_REJECT", payout_id, body.reason
    )
