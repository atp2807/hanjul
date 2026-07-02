"""서평단 마감임박 리마인더 — 기한 N일 내 ASSIGNED 리뷰어에게 ⏰ 알림(멱등)."""
import uuid
from datetime import datetime, timedelta, timezone

from main import remind_due_soon
from src.features.campaigns.infrastructure.campaign_repo import SqlCampaignRepository
from src.features.notifications.infrastructure.notification_repo import SqlNotificationRepository
from src.infrastructure.db.models.account import Account

UTC = timezone.utc


async def _assign(repo, reader_id, deadline):
    cid = await repo.create(uuid.uuid4(), uuid.uuid4(), 1, 7, 0)
    await repo.apply(cid, reader_id)
    await repo.assign(cid, reader_id, deadline)


async def test_due_soon_creates_reminder_idempotent(sessionmaker):
    async with sessionmaker() as s:
        reader = Account(display_name="리뷰어")
        s.add(reader)
        await s.commit()
        repo = SqlCampaignRepository(s)
        base = datetime(2026, 5, 1, tzinfo=UTC)

        await _assign(repo, reader.id, base + timedelta(days=1))   # 임박(2일 내)
        await _assign(repo, reader.id, base + timedelta(days=10))  # 멀어서 제외

        n = await remind_due_soon(s, base, within_days=2)
        assert n == 1  # 임박 1건만 알림

        notifs = SqlNotificationRepository(s)
        items = await notifs.list_for(reader.id)
        assert len([x for x in items if x.kind == "DUE_SOON"]) == 1

        # 재실행 → 멱등(중복 알림 없음)
        await remind_due_soon(s, base, within_days=2)
        items2 = await notifs.list_for(reader.id)
        assert len([x for x in items2 if x.kind == "DUE_SOON"]) == 1
