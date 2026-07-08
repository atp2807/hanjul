"""age_verification 서비스 — 고객(신청) + 운영자(심사: 승인·거부).

승인 시 usr.account.verified_tier_cd=AGE18 갱신은 accounts.AccountService(구조적 타이핑으로
AccountTierLookup 포트 만족)를 통해서만 이뤄진다 — "유저데이터는 accounts로만" 원칙(lr-66db3437).
"""
import logging
from datetime import UTC, datetime
from uuid import UUID

from src.features.age_verification.domain.models import (
    APPROVED,
    PENDING,
    REJECTED,
    AgeVerificationRepository,
    AgeVerificationRequestView,
    AlreadyPending,
    InvalidRequestState,
    RequestNotFound,
)

logger = logging.getLogger("app")


class AgeVerificationService:
    def __init__(self, repo: AgeVerificationRepository, storage, account_tier):
        self.repo = repo
        self.storage = storage  # id 사진 비공개 저장 어댑터(LocalDiskIdPhotoStorage)
        self.account_tier = account_tier  # AccountTierLookup + set_verified_tier(accounts.AccountService)

    # ── 고객 ──────────────────────────────────────────
    async def submit(self, account_id: UUID, data: bytes, ext: str) -> AgeVerificationRequestView:
        """신분증 사진 업로드 → 심사 요청. 계정당 진행중(PENDING) 1건만 허용(중복 방지)."""
        existing = await self.repo.get_pending_for_account(account_id)
        if existing is not None:
            raise AlreadyPending()
        key = await self.storage.save(data, ext)
        return await self.repo.create_request(account_id, key)

    async def my_request(self, account_id: UUID) -> AgeVerificationRequestView | None:
        return await self.repo.get_pending_for_account(account_id)

    # ── 운영자 ────────────────────────────────────────
    async def list_pending(self, status: str | None = PENDING) -> list[AgeVerificationRequestView]:
        return await self.repo.list_by_status(status)

    async def _require(self, request_id: UUID) -> AgeVerificationRequestView:
        req = await self.repo.get_request(request_id)
        if req is None:
            raise RequestNotFound()
        return req

    async def get_photo(self, request_id: UUID) -> tuple[bytes, str]:
        """심사용 원본 조회 — 이미 심사완료(삭제됨)면 RequestNotFound(404)."""
        req = await self._require(request_id)
        if req.id_photo_key is None:
            raise RequestNotFound()
        data = await self.storage.get(req.id_photo_key)
        if data is None:
            raise RequestNotFound()
        ext = req.id_photo_key.rsplit(".", 1)[-1]
        return data, ext

    async def approve(self, request_id: UUID, operator_id: UUID) -> None:
        req = await self._require(request_id)  # 없으면 404
        if not await self.repo.transition(request_id, (PENDING,), APPROVED, operator_id, self._now()):
            raise InvalidRequestState()
        await self.account_tier.set_verified_tier(req.account_id, "AGE18")
        await self._delete_photo(req)

    async def reject(self, request_id: UUID, operator_id: UUID) -> None:
        req = await self._require(request_id)
        if not await self.repo.transition(request_id, (PENDING,), REJECTED, operator_id, self._now()):
            raise InvalidRequestState()
        await self._delete_photo(req)

    async def _delete_photo(self, req: AgeVerificationRequestView) -> None:
        """심사 목적 외 원본 보관 금지 — 승인/거부 즉시 삭제. 실패해도 심사 결과는 유지, 로그만."""
        if req.id_photo_key is None:
            return
        try:
            await self.storage.delete(req.id_photo_key)
        except Exception:
            logger.exception(
                "신분증 이미지 삭제 실패 (request=%s) — 심사 결과는 정상 반영됨", req.id
            )

    @staticmethod
    def _now() -> datetime:
        return datetime.now(UTC)
