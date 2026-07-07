"""CampaignService 단위 — 신청/배정/차단/취소·마감 (Fake repo)."""
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from src.features.campaigns.application.campaign_service import CampaignService
from src.features.campaigns.domain.models import (
    OPERATOR_BLOCK_DAYS,
    CampaignNotFound,
    NoSlotsLeft,
    ReviewerBlocked,
)
from src.shared.errors import ValidationError

from tests.fixtures.fake_campaign_repo import FakeCampaignRepository

NOW = datetime(2026, 7, 1, tzinfo=UTC)


def _svc(repo: FakeCampaignRepository | None = None) -> tuple[CampaignService, FakeCampaignRepository]:
    repo = repo or FakeCampaignRepository()
    return CampaignService(repo), repo


# ── 생성 ──────────────────────────────────────────────
async def test_create_rejects_slots_below_one():
    svc, _ = _svc()
    with pytest.raises(ValidationError):
        await svc.create(uuid.uuid4(), uuid.uuid4(), slots=0)


async def test_create_returns_new_campaign_id():
    svc, repo = _svc()
    book_id, author_id = uuid.uuid4(), uuid.uuid4()

    campaign_id = await svc.create(book_id, author_id, slots=3, review_days=5, min_chars=100)

    view = await svc.get(campaign_id)
    assert view.book_id == book_id and view.author_id == author_id
    assert view.slots == 3 and view.review_days == 5 and view.min_chars == 100
    assert view.status == "OPEN"


# ── 조회 ──────────────────────────────────────────────
async def test_get_raises_not_found_for_missing_campaign():
    svc, _ = _svc()
    with pytest.raises(CampaignNotFound):
        await svc.get(uuid.uuid4())


# ── 신청 ──────────────────────────────────────────────
async def test_apply_rejected_when_campaign_not_open():
    svc, repo = _svc()
    campaign_id = repo.seed_campaign(status="CLOSED")

    with pytest.raises(NoSlotsLeft):
        await svc.apply(campaign_id, uuid.uuid4(), now=NOW)


async def test_apply_creates_pending_application_when_open():
    svc, repo = _svc()
    campaign_id = repo.seed_campaign(status="OPEN", slots=2, filled=0)
    applicant = uuid.uuid4()

    await svc.apply(campaign_id, applicant, now=NOW)

    apps = await svc.list_my_applications(applicant, now=NOW)
    assert len(apps) == 1 and apps[0].status == "PENDING" and apps[0].campaign_id == campaign_id


async def test_apply_rejected_when_reviewer_blocked():
    svc, repo = _svc()
    campaign_id = repo.seed_campaign(status="OPEN")
    applicant = uuid.uuid4()
    until = NOW + timedelta(days=10)
    await repo.block_reviewer(applicant, until)

    with pytest.raises(ReviewerBlocked) as exc:
        await svc.apply(campaign_id, applicant, now=NOW)
    assert exc.value.until == until


async def test_apply_allowed_after_block_expires():
    svc, repo = _svc()
    campaign_id = repo.seed_campaign(status="OPEN")
    applicant = uuid.uuid4()
    await repo.block_reviewer(applicant, NOW - timedelta(days=1))  # 이미 만료

    await svc.apply(campaign_id, applicant, now=NOW)  # 예외 없이 통과

    apps = await svc.list_my_applications(applicant, now=NOW)
    assert len(apps) == 1


# ── 배정 ──────────────────────────────────────────────
async def test_assign_computes_deadline_from_review_days():
    svc, repo = _svc()
    campaign_id = repo.seed_campaign(status="OPEN", slots=2, filled=0, review_days=5)
    applicant = uuid.uuid4()
    repo.seed_application(campaign_id, applicant, status="PENDING")

    ok = await svc.assign(campaign_id, applicant, now=NOW)

    assert ok is True
    app = next(a for a in repo.applications.values() if a["applicant_id"] == applicant)
    assert app["status"] == "ASSIGNED"
    assert app["deadline_at"] == NOW + timedelta(days=5)


async def test_assign_raises_no_slots_left_when_repo_declines():
    svc, repo = _svc()
    campaign_id = repo.seed_campaign(status="OPEN", slots=1, filled=1)  # 슬롯 소진
    applicant = uuid.uuid4()
    repo.seed_application(campaign_id, applicant, status="PENDING")

    with pytest.raises(NoSlotsLeft):
        await svc.assign(campaign_id, applicant, now=NOW)


async def test_assign_raises_campaign_not_found():
    svc, _ = _svc()
    with pytest.raises(CampaignNotFound):
        await svc.assign(uuid.uuid4(), uuid.uuid4(), now=NOW)


# ── 취소/마감 ─────────────────────────────────────────
async def test_cancel_removes_pending_application():
    svc, repo = _svc()
    campaign_id = repo.seed_campaign(status="OPEN")
    applicant = uuid.uuid4()
    repo.seed_application(campaign_id, applicant, status="PENDING")

    assert await svc.cancel(campaign_id, applicant) is True
    assert await svc.list_my_applications(applicant, now=NOW) == []


async def test_cancel_returns_false_when_already_assigned():
    svc, repo = _svc()
    campaign_id = repo.seed_campaign(status="OPEN")
    applicant = uuid.uuid4()
    repo.seed_application(campaign_id, applicant, status="ASSIGNED")

    assert await svc.cancel(campaign_id, applicant) is False


async def test_close_sets_campaign_closed():
    svc, repo = _svc()
    campaign_id = repo.seed_campaign(status="OPEN")

    await svc.close(campaign_id)

    view = await svc.get(campaign_id)
    assert view.status == "CLOSED"


# ── 리뷰 완료 ─────────────────────────────────────────
async def test_mark_review_done_marks_assigned_completed():
    svc, repo = _svc()
    book_id = uuid.uuid4()
    campaign_id = repo.seed_campaign(book_id=book_id, status="OPEN")
    applicant = uuid.uuid4()
    repo.seed_application(campaign_id, applicant, status="ASSIGNED")

    await svc.mark_review_done(book_id, applicant)

    app = next(a for a in repo.applications.values() if a["applicant_id"] == applicant)
    assert app["status"] == "COMPLETED"


# ── 운영자 자격회수(block/unblock) ────────────────────
async def test_block_reviewer_sets_far_future_expiry():
    svc, repo = _svc()
    account_id = uuid.uuid4()

    await svc.block_reviewer(account_id, now=NOW)

    assert repo.blocks[account_id] == NOW + timedelta(days=OPERATOR_BLOCK_DAYS)


async def test_unblock_reviewer_clears_block():
    svc, repo = _svc()
    account_id = uuid.uuid4()
    await repo.block_reviewer(account_id, NOW + timedelta(days=10))

    await svc.unblock_reviewer(account_id)

    assert account_id not in repo.blocks


async def test_reviewer_blocked_until_returns_value_when_active():
    svc, repo = _svc()
    account_id = uuid.uuid4()
    until = NOW + timedelta(days=5)
    await repo.block_reviewer(account_id, until)

    assert await svc.reviewer_blocked_until(account_id, now=NOW) == until


async def test_reviewer_blocked_until_returns_none_when_expired():
    svc, repo = _svc()
    account_id = uuid.uuid4()
    await repo.block_reviewer(account_id, NOW - timedelta(days=1))

    assert await svc.reviewer_blocked_until(account_id, now=NOW) is None
