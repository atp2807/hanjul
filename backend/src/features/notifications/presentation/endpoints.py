"""notifications API — 작가 팔로우 + 인앱 알림함."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import get_session
from src.features.auth.domain.models import AccountPrincipal
from src.features.auth.infrastructure.account_repo import SqlAccountRepository
from src.features.auth.presentation.dependencies import get_current_account
from src.features.notifications.application.notification_service import NotificationService
from src.features.notifications.presentation.dependencies import get_notification_service
from src.features.notifications.presentation.schemas import (
    FollowStatusResponse,
    NotificationItem,
    NotificationListResponse,
)

router = APIRouter(tags=["notifications"])


# ── 작가 팔로우 ───────────────────────────────────────
@router.post("/authors/{author_id}/follow", status_code=204)
async def follow_author(
    author_id: UUID,
    principal: AccountPrincipal = Depends(get_current_account),
    svc: NotificationService = Depends(get_notification_service),
    session: AsyncSession = Depends(get_session),
) -> None:
    """작가 팔로우 — 신간 출판 시 알림. 없는 작가 404 / 자기 자신 400."""
    if await SqlAccountRepository(session).get_account(author_id) is None:
        raise HTTPException(404, "author not found")
    try:
        await svc.follow(principal.id, author_id)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.delete("/authors/{author_id}/follow", status_code=204)
async def unfollow_author(
    author_id: UUID,
    principal: AccountPrincipal = Depends(get_current_account),
    svc: NotificationService = Depends(get_notification_service),
) -> None:
    await svc.unfollow(principal.id, author_id)


@router.get("/authors/{author_id}/follow", response_model=FollowStatusResponse)
async def follow_status(
    author_id: UUID,
    principal: AccountPrincipal = Depends(get_current_account),
    svc: NotificationService = Depends(get_notification_service),
) -> FollowStatusResponse:
    return FollowStatusResponse(following=await svc.is_following(principal.id, author_id))


# ── 알림함 ────────────────────────────────────────────
@router.get("/me/notifications", response_model=NotificationListResponse)
async def my_notifications(
    principal: AccountPrincipal = Depends(get_current_account),
    svc: NotificationService = Depends(get_notification_service),
) -> NotificationListResponse:
    items, unread = await svc.inbox(principal.id)
    return NotificationListResponse(
        items=[NotificationItem.model_validate(n) for n in items], unread_count=unread
    )


@router.post("/me/notifications/{notification_id}/read", status_code=204)
async def read_notification(
    notification_id: UUID,
    principal: AccountPrincipal = Depends(get_current_account),
    svc: NotificationService = Depends(get_notification_service),
) -> None:
    if not await svc.mark_read(principal.id, notification_id):
        raise HTTPException(404, "notification not found")


@router.post("/me/notifications/read-all", status_code=204)
async def read_all_notifications(
    principal: AccountPrincipal = Depends(get_current_account),
    svc: NotificationService = Depends(get_notification_service),
) -> None:
    await svc.mark_all_read(principal.id)
