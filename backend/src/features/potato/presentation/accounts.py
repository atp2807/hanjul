"""potato API — 계정 조치. 정지=accounts 소유 / 서평단 자격회수=campaigns 소유. + 감사."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request

from src.features.accounts.application.account_service import AccountService
from src.features.accounts.domain.models import AccountNotFound
from src.features.accounts.presentation.dependencies import get_account_service
from src.features.campaigns.application.campaign_service import CampaignService
from src.features.campaigns.presentation.dependencies import get_campaign_service
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
    campaigns: CampaignService = Depends(get_campaign_service),
) -> AccountModerationView:
    """계정 모더레이션 뷰. 정지상태=accounts, 서평단 차단=campaigns(commu.reviewer_block)."""
    try:
        acc = await accounts.get_profile(account_id)
    except AccountNotFound:
        raise HTTPException(404, "account not found")
    blocked_until = await campaigns.reviewer_blocked_until(account_id)
    return AccountModerationView(
        id=acc.id,
        email=acc.email,
        display_name=acc.display_name,
        role_cd=acc.role_cd,
        status_cd=acc.status_cd,
        review_blocked=blocked_until is not None,
        review_blocked_at=blocked_until,
    )


@router.post("/accounts/{account_id}/suspend", status_code=204)
async def suspend(
    account_id: UUID,
    request: Request,
    body: ReasonRequest = ReasonRequest(),
    op: OperatorPrincipal = Depends(get_current_operator),
    accounts: AccountService = Depends(get_account_service),
    audit: AuditService = Depends(get_audit_service),
) -> None:
    try:
        await accounts.suspend(account_id)
    except AccountNotFound:
        raise HTTPException(404, "account not found")
    await audit.record(op.id, "SUSPEND", "ACCOUNT", account_id, {"reason": body.reason}, _client_ip(request))


@router.post("/accounts/{account_id}/unsuspend", status_code=204)
async def unsuspend(
    account_id: UUID,
    request: Request,
    op: OperatorPrincipal = Depends(get_current_operator),
    accounts: AccountService = Depends(get_account_service),
    audit: AuditService = Depends(get_audit_service),
) -> None:
    try:
        await accounts.unsuspend(account_id)
    except AccountNotFound:
        raise HTTPException(404, "account not found")
    await audit.record(op.id, "UNSUSPEND", "ACCOUNT", account_id, None, _client_ip(request))


@router.post("/accounts/{account_id}/block-review", status_code=204)
async def block_review(
    account_id: UUID,
    request: Request,
    body: ReasonRequest = ReasonRequest(),
    op: OperatorPrincipal = Depends(get_current_operator),
    accounts: AccountService = Depends(get_account_service),
    campaigns: CampaignService = Depends(get_campaign_service),
    audit: AuditService = Depends(get_audit_service),
) -> None:
    """서평단 자격회수 — campaigns 소유(commu.reviewer_block)."""
    if not await accounts.exists(account_id):
        raise HTTPException(404, "account not found")
    await campaigns.block_reviewer(account_id)
    await audit.record(op.id, "BLOCK_REVIEW", "ACCOUNT", account_id, {"reason": body.reason}, _client_ip(request))


@router.post("/accounts/{account_id}/unblock-review", status_code=204)
async def unblock_review(
    account_id: UUID,
    request: Request,
    op: OperatorPrincipal = Depends(get_current_operator),
    accounts: AccountService = Depends(get_account_service),
    campaigns: CampaignService = Depends(get_campaign_service),
    audit: AuditService = Depends(get_audit_service),
) -> None:
    if not await accounts.exists(account_id):
        raise HTTPException(404, "account not found")
    await campaigns.unblock_reviewer(account_id)
    await audit.record(op.id, "UNBLOCK_REVIEW", "ACCOUNT", account_id, None, _client_ip(request))
