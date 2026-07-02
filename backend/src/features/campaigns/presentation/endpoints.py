"""campaigns API — 서평단 캠페인 생성·모집·신청·배정."""
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import get_session
from src.features.accounts.application.account_service import AccountService
from src.features.accounts.presentation.dependencies import get_account_service
from src.features.auth.domain.models import AccountPrincipal
from src.features.auth.presentation.dependencies import get_current_account
from src.features.billing.application.order_service import OrderService
from src.features.billing.presentation.dependencies import get_order_service
from src.features.campaigns.application.campaign_service import CampaignService
from src.features.campaigns.infrastructure.campaign_repo import SqlCampaignRepository
from src.features.campaigns.presentation.dependencies import get_campaign_service
from src.features.campaigns.presentation.schemas import (
    ApplicantItem,
    ApplicantListResponse,
    ApplicationItem,
    ApplicationListResponse,
    AssignRequest,
    AuthorCampaignItem,
    AuthorCampaignListResponse,
    CampaignItem,
    CampaignListResponse,
    CreateCampaignRequest,
    ReviewerStatusResponse,
)
from src.features.notifications.application.notification_service import NotificationService
from src.features.notifications.presentation.dependencies import get_notification_service
from src.shared.errors import ConflictError, ForbiddenError, NotFoundError

router = APIRouter(tags=["campaigns"])


@router.post("/campaigns", status_code=201)
async def create_campaign(
    body: CreateCampaignRequest,
    principal: AccountPrincipal = Depends(get_current_account),
    svc: CampaignService = Depends(get_campaign_service),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """서평단 캠페인 생성 — 책의 작가 본인만."""
    author = await SqlCampaignRepository(session).book_author(body.book_id)
    if author is None:
        raise NotFoundError("book not found")
    if author != principal.id:
        raise ForbiddenError("이 책의 작가만 서평단을 열 수 있어요")
    cid = await svc.create(body.book_id, principal.id, body.slots, body.review_days, body.min_chars)
    return {"campaignId": str(cid)}


@router.get("/campaigns/open", response_model=CampaignListResponse)
async def list_open(
    category: str | None = None,
    svc: CampaignService = Depends(get_campaign_service),
) -> CampaignListResponse:
    """모집중 캠페인 — category 지정 시 그 장르만."""
    items = await svc.list_open(category)
    return CampaignListResponse(items=[CampaignItem.model_validate(c) for c in items])


@router.get("/me/campaigns", response_model=AuthorCampaignListResponse)
async def my_campaigns(
    principal: AccountPrincipal = Depends(get_current_account),
    svc: CampaignService = Depends(get_campaign_service),
) -> AuthorCampaignListResponse:
    """작가 본인의 캠페인 목록 + 신청/완료 집계 (관리 대시보드)."""
    items = await svc.list_for_author(principal.id)
    return AuthorCampaignListResponse(items=[AuthorCampaignItem.model_validate(c) for c in items])


@router.get("/campaigns/{campaign_id}", response_model=CampaignItem)
async def campaign_detail(
    campaign_id: UUID,
    svc: CampaignService = Depends(get_campaign_service),
) -> CampaignItem:
    """캠페인 상세 (공개)."""
    camp = await svc.get(campaign_id)
    return CampaignItem.model_validate(camp)


@router.get("/campaigns/{campaign_id}/applications", response_model=ApplicantListResponse)
async def campaign_applicants(
    campaign_id: UUID,
    principal: AccountPrincipal = Depends(get_current_account),
    svc: CampaignService = Depends(get_campaign_service),
    acct: AccountService = Depends(get_account_service),
) -> ApplicantListResponse:
    """캠페인 신청자 목록 — 캠페인 작가만 (배정 UI)."""
    camp = await svc.get(campaign_id)
    if camp.author_id != principal.id:
        raise ForbiddenError("이 캠페인의 작가만 볼 수 있어요")
    items = await svc.list_applicants(campaign_id)
    names = await acct.names_for([a.applicant_id for a in items])  # 직접 JOIN 대체
    return ApplicantListResponse(
        items=[
            ApplicantItem(
                id=a.id, applicant_id=a.applicant_id, applicant_name=names.get(a.applicant_id),
                status_cd=a.status_cd, deadline_at=a.deadline_at, created_at=a.created_at,
            )
            for a in items
        ]
    )


@router.post("/campaigns/{campaign_id}/close", status_code=204)
async def close_campaign(
    campaign_id: UUID,
    principal: AccountPrincipal = Depends(get_current_account),
    svc: CampaignService = Depends(get_campaign_service),
) -> None:
    """모집 수동 마감 — 캠페인 작가만. 피드 제외 + 새 신청 차단(기존 신청자는 배정 가능)."""
    camp = await svc.get(campaign_id)
    if camp.author_id != principal.id:
        raise ForbiddenError("이 캠페인의 작가만 마감할 수 있어요")
    await svc.close(campaign_id)


@router.delete("/campaigns/{campaign_id}/apply", status_code=204)
async def cancel_application(
    campaign_id: UUID,
    principal: AccountPrincipal = Depends(get_current_account),
    svc: CampaignService = Depends(get_campaign_service),
) -> None:
    """리뷰어 신청 취소 — 아직 배정 전(PENDING)만."""
    ok = await svc.cancel(campaign_id, principal.id)
    if not ok:
        raise ConflictError("이미 배정됐거나 신청 내역이 없어요")


@router.post("/campaigns/{campaign_id}/apply", status_code=204)
async def apply(
    campaign_id: UUID,
    principal: AccountPrincipal = Depends(get_current_account),
    svc: CampaignService = Depends(get_campaign_service),
) -> None:
    """리뷰어 신청 (모집중인 캠페인)."""
    await svc.apply(campaign_id, principal.id)


@router.post("/campaigns/{campaign_id}/assign", status_code=204)
async def assign(
    campaign_id: UUID,
    body: AssignRequest,
    principal: AccountPrincipal = Depends(get_current_account),
    svc: CampaignService = Depends(get_campaign_service),
    orders: OrderService = Depends(get_order_service),
    notifs: NotificationService = Depends(get_notification_service),
) -> None:
    """리뷰어 배정 — 캠페인 작가만. 배정 성공 시 증정본 지급 + 리뷰어 알림."""
    camp = await svc.get(campaign_id)
    if camp.author_id != principal.id:
        raise ForbiddenError("이 캠페인의 작가만 배정할 수 있어요")
    await svc.assign(campaign_id, body.applicant_id)
    await orders.grant_review_copy(camp.book_id, body.applicant_id)  # 증정본 지급
    await notifs.notify_assigned(body.applicant_id, camp.book_id, camp.book_title)  # 배정 알림


@router.get("/me/reviewer-status", response_model=ReviewerStatusResponse)
async def reviewer_status(
    principal: AccountPrincipal = Depends(get_current_account),
    svc: CampaignService = Depends(get_campaign_service),
) -> ReviewerStatusResponse:
    """리뷰어 신뢰도·자격 — 완료/미작성/완료율/자격회수."""
    s = await svc.reviewer_status(principal.id)
    return ReviewerStatusResponse.model_validate(s)


@router.get("/me/applications", response_model=ApplicationListResponse)
async def my_applications(
    principal: AccountPrincipal = Depends(get_current_account),
    svc: CampaignService = Depends(get_campaign_service),
) -> ApplicationListResponse:
    items = await svc.list_my_applications(principal.id)
    return ApplicationListResponse(items=[ApplicationItem.model_validate(a) for a in items])
