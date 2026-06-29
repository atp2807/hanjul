"""potato API — 계정 조치 (정지 / 서평단 자격회수). accounts 서비스에 위임 + 감사."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request

from src.features.accounts.application.account_service import AccountService
from src.features.accounts.domain.models import AccountNotFound
from src.features.accounts.presentation.dependencies import get_account_service
from src.features.potato.application.audit import AuditService
from src.features.potato.domain.models import OperatorPrincipal
from src.features.potato.presentation.dependencies import (
    get_audit_service,
    get_current_operator,
)
from src.features.potato.presentation.schemas import AccountModerationView, ReasonRequest

router = APIRouter(prefix="/potato", tags=["potato"])


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


@router.get("/accounts/{account_id}", response_model=AccountModerationView)
async def view_account(
    account_id: UUID,
    _op: OperatorPrincipal = Depends(get_current_operator),
    accounts: AccountService = Depends(get_account_service),
) -> AccountModerationView:
    """계정 모더레이션 뷰 (신고 처리 시 대상 확인용)."""
    try:
        acc = await accounts.get_profile(account_id)
    except AccountNotFound:
        raise HTTPException(404, "account not found")
    return AccountModerationView(
        id=acc.id,
        email=acc.email,
        display_name=acc.display_name,
        role_cd=acc.role_cd,
        status_cd=acc.status_cd,
        review_blocked=acc.review_blocked_at is not None,
        review_blocked_at=acc.review_blocked_at,
    )


async def _act(
    account_id: UUID,
    request: Request,
    op: OperatorPrincipal,
    audit: AuditService,
    coro,
    action: str,
    reason: str | None,
) -> None:
    try:
        await coro
    except AccountNotFound:
        raise HTTPException(404, "account not found")
    await audit.record(op.id, action, "ACCOUNT", account_id, {"reason": reason}, _client_ip(request))


@router.post("/accounts/{account_id}/suspend", status_code=204)
async def suspend(
    account_id: UUID,
    request: Request,
    body: ReasonRequest = ReasonRequest(),
    op: OperatorPrincipal = Depends(get_current_operator),
    accounts: AccountService = Depends(get_account_service),
    audit: AuditService = Depends(get_audit_service),
) -> None:
    await _act(account_id, request, op, audit, accounts.suspend(account_id), "SUSPEND", body.reason)


@router.post("/accounts/{account_id}/unsuspend", status_code=204)
async def unsuspend(
    account_id: UUID,
    request: Request,
    op: OperatorPrincipal = Depends(get_current_operator),
    accounts: AccountService = Depends(get_account_service),
    audit: AuditService = Depends(get_audit_service),
) -> None:
    await _act(account_id, request, op, audit, accounts.unsuspend(account_id), "UNSUSPEND", None)


@router.post("/accounts/{account_id}/block-review", status_code=204)
async def block_review(
    account_id: UUID,
    request: Request,
    body: ReasonRequest = ReasonRequest(),
    op: OperatorPrincipal = Depends(get_current_operator),
    accounts: AccountService = Depends(get_account_service),
    audit: AuditService = Depends(get_audit_service),
) -> None:
    await _act(
        account_id, request, op, audit, accounts.block_review(account_id), "BLOCK_REVIEW", body.reason
    )


@router.post("/accounts/{account_id}/unblock-review", status_code=204)
async def unblock_review(
    account_id: UUID,
    request: Request,
    op: OperatorPrincipal = Depends(get_current_operator),
    accounts: AccountService = Depends(get_account_service),
    audit: AuditService = Depends(get_audit_service),
) -> None:
    await _act(
        account_id, request, op, audit, accounts.unblock_review(account_id), "UNBLOCK_REVIEW", None
    )
