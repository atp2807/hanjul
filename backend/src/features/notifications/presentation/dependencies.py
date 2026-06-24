"""notifications 표현 레이어 DI."""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import get_session
from src.features.notifications.application.notification_service import NotificationService
from src.features.notifications.infrastructure.notification_repo import (
    SqlFollowRepository,
    SqlNotificationRepository,
)


def get_notification_service(session: AsyncSession = Depends(get_session)) -> NotificationService:
    return NotificationService(SqlFollowRepository(session), SqlNotificationRepository(session))
