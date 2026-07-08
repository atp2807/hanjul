"""AgeVerificationService 단위 — 신청(중복방지) + 운영자 승인/거부(+원본삭제) (Fake repo/storage)."""
import uuid
from datetime import UTC, datetime

import pytest
from src.features.age_verification.application.age_verification_service import (
    AgeVerificationService,
)
from src.features.age_verification.domain.models import (
    APPROVED,
    PENDING,
    REJECTED,
    AgeVerificationRequestView,
    AlreadyPending,
    InvalidRequestState,
    RequestNotFound,
)

from tests.fixtures.fake_age_verification_repo import FakeAgeVerificationRepository

NOW = datetime(2026, 7, 8, tzinfo=UTC)


class FakeIdPhotoStorage:
    """save/get/delete — 삭제 여부를 assert할 수 있도록 deleted 목록을 남긴다."""

    def __init__(self, fail_delete: bool = False) -> None:
        self.files: dict[str, bytes] = {}
        self.deleted: list[str] = []
        self.fail_delete = fail_delete

    async def save(self, data: bytes, ext: str) -> str:
        key = f"{uuid.uuid4().hex}.{ext}"
        self.files[key] = data
        return key

    async def get(self, key: str) -> bytes | None:
        return self.files.get(key)

    async def delete(self, key: str) -> None:
        if self.fail_delete:
            raise OSError("disk error")
        self.files.pop(key, None)
        self.deleted.append(key)


class FakeAccountTier:
    def __init__(self) -> None:
        self.tiers: dict = {}

    async def get_verified_tier(self, account_id) -> str:
        return self.tiers.get(account_id, "ALL")

    async def set_verified_tier(self, account_id, tier: str) -> None:
        self.tiers[account_id] = tier


def _request(account_id, status=PENDING, id_photo_key="abc.jpg") -> AgeVerificationRequestView:
    return AgeVerificationRequestView(
        id=uuid.uuid4(), account_id=account_id, status=status,
        id_photo_key=id_photo_key, created_at=NOW,
    )


# ── 고객: 신청 ────────────────────────────────────────
async def test_submit_creates_pending_request():
    repo, storage, tier = FakeAgeVerificationRepository(), FakeIdPhotoStorage(), FakeAccountTier()
    svc = AgeVerificationService(repo, storage, tier)
    account_id = uuid.uuid4()

    req = await svc.submit(account_id, b"jpeg-bytes", "jpg")

    assert req.status == PENDING
    assert req.account_id == account_id
    assert storage.files[req.id_photo_key] == b"jpeg-bytes"


async def test_submit_rejects_duplicate_pending():
    repo, storage, tier = FakeAgeVerificationRepository(), FakeIdPhotoStorage(), FakeAccountTier()
    svc = AgeVerificationService(repo, storage, tier)
    account_id = uuid.uuid4()
    await svc.submit(account_id, b"jpeg-bytes", "jpg")

    with pytest.raises(AlreadyPending):
        await svc.submit(account_id, b"more-bytes", "png")


async def test_my_request_returns_none_when_no_pending():
    svc = AgeVerificationService(FakeAgeVerificationRepository(), FakeIdPhotoStorage(), FakeAccountTier())
    assert await svc.my_request(uuid.uuid4()) is None


# ── 운영자: 승인 ──────────────────────────────────────
async def test_approve_updates_tier_and_deletes_photo():
    repo, storage, tier = FakeAgeVerificationRepository(), FakeIdPhotoStorage(), FakeAccountTier()
    account_id = uuid.uuid4()
    req = _request(account_id)
    photo_key = req.id_photo_key  # seed()는 참조를 그대로 저장하므로 값을 먼저 캡처해둔다
    repo.seed(req)
    storage.files[photo_key] = b"jpeg-bytes"
    svc = AgeVerificationService(repo, storage, tier)

    await svc.approve(req.id, operator_id=uuid.uuid4())

    assert repo.requests[req.id].status == APPROVED
    assert repo.requests[req.id].id_photo_key is None  # DB 참조도 제거됨
    assert tier.tiers[account_id] == "AGE18"
    assert photo_key in storage.deleted  # 원본 실제 삭제됨
    assert photo_key not in storage.files


async def test_approve_missing_request_raises_not_found():
    svc = AgeVerificationService(FakeAgeVerificationRepository(), FakeIdPhotoStorage(), FakeAccountTier())
    with pytest.raises(RequestNotFound):
        await svc.approve(uuid.uuid4(), operator_id=uuid.uuid4())


async def test_approve_already_reviewed_raises_invalid_state():
    repo, storage, tier = FakeAgeVerificationRepository(), FakeIdPhotoStorage(), FakeAccountTier()
    req = _request(uuid.uuid4(), status=APPROVED, id_photo_key=None)
    repo.seed(req)
    svc = AgeVerificationService(repo, storage, tier)

    with pytest.raises(InvalidRequestState):
        await svc.approve(req.id, operator_id=uuid.uuid4())


async def test_approve_continues_when_photo_delete_fails(caplog):
    """삭제 실패해도 심사 결과(승인+등급갱신)는 유지되고, 로그만 남는다."""
    repo = FakeAgeVerificationRepository()
    storage = FakeIdPhotoStorage(fail_delete=True)
    tier = FakeAccountTier()
    account_id = uuid.uuid4()
    req = _request(account_id)
    repo.seed(req)
    svc = AgeVerificationService(repo, storage, tier)

    await svc.approve(req.id, operator_id=uuid.uuid4())  # 예외 안 남

    assert repo.requests[req.id].status == APPROVED
    assert tier.tiers[account_id] == "AGE18"


# ── 운영자: 거부 ──────────────────────────────────────
async def test_reject_deletes_photo_without_tier_change():
    repo, storage, tier = FakeAgeVerificationRepository(), FakeIdPhotoStorage(), FakeAccountTier()
    account_id = uuid.uuid4()
    req = _request(account_id)
    photo_key = req.id_photo_key  # seed()는 참조를 그대로 저장하므로 값을 먼저 캡처해둔다
    repo.seed(req)
    storage.files[photo_key] = b"jpeg-bytes"
    svc = AgeVerificationService(repo, storage, tier)

    await svc.reject(req.id, operator_id=uuid.uuid4())

    assert repo.requests[req.id].status == REJECTED
    assert repo.requests[req.id].id_photo_key is None
    assert account_id not in tier.tiers  # 거부는 등급 변경 없음
    assert photo_key in storage.deleted


async def test_reject_already_reviewed_raises_invalid_state():
    repo, storage, tier = FakeAgeVerificationRepository(), FakeIdPhotoStorage(), FakeAccountTier()
    req = _request(uuid.uuid4(), status=REJECTED, id_photo_key=None)
    repo.seed(req)
    svc = AgeVerificationService(repo, storage, tier)

    with pytest.raises(InvalidRequestState):
        await svc.reject(req.id, operator_id=uuid.uuid4())


# ── 운영자: 조회 ──────────────────────────────────────
async def test_list_pending_defaults_to_pending_only():
    repo, storage, tier = FakeAgeVerificationRepository(), FakeIdPhotoStorage(), FakeAccountTier()
    pending = _request(uuid.uuid4(), status=PENDING)
    approved = _request(uuid.uuid4(), status=APPROVED, id_photo_key=None)
    repo.seed(pending)
    repo.seed(approved)
    svc = AgeVerificationService(repo, storage, tier)

    items = await svc.list_pending()

    assert [i.id for i in items] == [pending.id]


async def test_get_photo_returns_bytes_and_ext():
    repo, storage, tier = FakeAgeVerificationRepository(), FakeIdPhotoStorage(), FakeAccountTier()
    req = _request(uuid.uuid4(), id_photo_key="xyz.png")
    repo.seed(req)
    storage.files["xyz.png"] = b"png-bytes"
    svc = AgeVerificationService(repo, storage, tier)

    data, ext = await svc.get_photo(req.id)

    assert data == b"png-bytes"
    assert ext == "png"


async def test_get_photo_after_review_raises_not_found():
    """심사완료(원본 삭제됨) 후 사진 조회 → 404 (오조회 방지)."""
    repo, storage, tier = FakeAgeVerificationRepository(), FakeIdPhotoStorage(), FakeAccountTier()
    req = _request(uuid.uuid4())
    repo.seed(req)
    storage.files[req.id_photo_key] = b"jpeg-bytes"
    svc = AgeVerificationService(repo, storage, tier)
    await svc.approve(req.id, operator_id=uuid.uuid4())

    with pytest.raises(RequestNotFound):
        await svc.get_photo(req.id)
