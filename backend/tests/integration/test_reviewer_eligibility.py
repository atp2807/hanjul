"""서평단 자격회수 — 미작성(EXPIRED) 누적 → 신청 제한."""
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from src.features.campaigns.application.campaign_service import CampaignService
from src.features.campaigns.domain.models import ReviewerBlocked
from src.features.campaigns.infrastructure.campaign_repo import SqlCampaignRepository
from src.infrastructure.db.models.account import Account

UTC = timezone.utc


async def _expire_one(repo, reader_id, base):
    """캠페인 하나에 신청·배정(과거 마감)해서 미작성 1건을 만든다."""
    cid = await repo.create(uuid.uuid4(), uuid.uuid4(), 1, 7, 0)
    await repo.apply(cid, reader_id)
    await repo.assign(cid, reader_id, base)  # deadline=base(과거)


async def test_two_misses_revoke_eligibility(sessionmaker):
    async with sessionmaker() as s:
        reader = Account(display_name="리뷰어")
        s.add(reader)
        await s.commit()
        repo = SqlCampaignRepository(s)
        svc = CampaignService(repo)
        base = datetime(2026, 1, 1, tzinfo=UTC)
        future = base + timedelta(days=10)

        # 미작성 1건 → 아직 정상
        await _expire_one(repo, reader.id, base)
        st1 = await svc.reviewer_status(reader.id, future)
        assert st1.missed == 1 and st1.completion_rate == 0 and st1.blocked_until is None

        # 미작성 2건 → 자격회수
        await _expire_one(repo, reader.id, base)
        st2 = await svc.reviewer_status(reader.id, future)
        assert st2.missed == 2 and st2.blocked_until is not None

        # 회수 기간 중 신청 차단
        open_cid = await repo.create(uuid.uuid4(), uuid.uuid4(), 5, 7, 0)
        with pytest.raises(ReviewerBlocked):
            await svc.apply(open_cid, reader.id, now=future)


async def test_block_resets_after_recovery(sessionmaker):
    """차단 해제 후 미작성 1건만으론 재차단 안 됨(사이클별 카운트)."""
    async with sessionmaker() as s:
        reader = Account(display_name="회복")
        s.add(reader)
        await s.commit()
        repo = SqlCampaignRepository(s)
        svc = CampaignService(repo)
        base = datetime(2026, 1, 1, tzinfo=UTC)
        t1 = base + timedelta(days=10)

        # 2회 미작성 → 차단 (해제 = t1 + 14일)
        await _expire_one(repo, reader.id, base)
        await _expire_one(repo, reader.id, base)
        st = await svc.reviewer_status(reader.id, t1)
        assert st.blocked_until is not None
        unblock = st.blocked_until

        after = unblock + timedelta(days=1)  # 차단 해제 이후
        # 해제 후 미작성 1건 → 재차단 안 됨
        await _expire_one(repo, reader.id, unblock + timedelta(hours=1))
        st2 = await svc.reviewer_status(reader.id, after)
        assert st2.blocked_until is None, "회복 후 1회 미작성은 재차단 아님"

        # 해제 후 2건째 → 재차단
        await _expire_one(repo, reader.id, unblock + timedelta(hours=2))
        st3 = await svc.reviewer_status(reader.id, after)
        assert st3.blocked_until is not None


async def test_completion_counts_toward_rate(sessionmaker):
    async with sessionmaker() as s:
        reader = Account(display_name="성실")
        s.add(reader)
        await s.commit()
        repo = SqlCampaignRepository(s)
        svc = CampaignService(repo)
        now = datetime(2026, 3, 1, tzinfo=UTC)

        # 기한 내 완료 1건(미래 마감 → 만료 안 됨), 리뷰 작성 처리
        book = uuid.uuid4()
        cid = await repo.create(book, uuid.uuid4(), 1, 7, 0)
        await repo.apply(cid, reader.id)
        await repo.assign(cid, reader.id, now + timedelta(days=7))
        await repo.mark_completed(book, reader.id)

        st = await svc.reviewer_status(reader.id, now)
        assert st.completed == 1 and st.missed == 0 and st.completion_rate == 100
        assert st.blocked_until is None
