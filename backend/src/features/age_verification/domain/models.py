"""age_verification 도메인 — 성인인증(AGE18) 신청 상태기계 + 에러.

흐름: 신분증 사진 업로드(PENDING, 계정당 진행중 1건만) → potato 운영자 승인(APPROVED,
usr.account.verified_tier_cd=AGE18로 갱신) 또는 거부(REJECTED). 승인·거부 어느 쪽이든
심사 완료 즉시 원본 이미지를 삭제한다(심사 목적 외 보관 금지 — application 레이어가 처리).
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from src.shared.errors import ConflictError, NotFoundError, ValidationError

PENDING = "PENDING"
APPROVED = "APPROVED"
REJECTED = "REJECTED"


@dataclass
class AgeVerificationRequestView:
    id: UUID
    account_id: UUID
    status: str
    # 신분증 사진 저장 키(비공개 스토리지). 심사완료(APPROVED/REJECTED) 즉시 None으로 되돌아감.
    id_photo_key: str | None
    created_at: datetime
    reviewed_at: datetime | None = None
    reviewed_by: UUID | None = None


class AlreadyPending(ConflictError):
    """이미 심사 중인 요청이 있어 중복 제출 불가 (409)."""

    default_detail = "이미 심사 중인 성인인증 요청이 있어요."


class InvalidImageFile(ValidationError):
    """이미지 파일이 아니거나 크기 제한 초과 (422)."""

    default_detail = "이미지 파일만 업로드할 수 있어요 (PNG·JPG·WebP, 5MB 이하)."


class RequestNotFound(NotFoundError):
    """요청이 없거나(오탐 방지 위해 이미 삭제된 사진 조회도 이걸로 통일) → 404."""

    default_detail = "인증 요청을 찾을 수 없어요."


class InvalidRequestState(ConflictError):
    """이미 심사완료(APPROVED/REJECTED)된 요청을 다시 승인/거부 시도 → 409."""

    default_detail = "이미 처리된 요청이에요."


class AgeVerificationRepository(Protocol):
    async def get_pending_for_account(self, account_id: UUID) -> AgeVerificationRequestView | None:
        """계정의 진행중(PENDING) 요청. 없으면 None (계정당 1건 제약 확인용)."""
        ...

    async def create_request(self, account_id: UUID, id_photo_key: str) -> AgeVerificationRequestView:
        ...

    async def get_request(self, request_id: UUID) -> AgeVerificationRequestView | None:
        ...

    async def list_by_status(self, status: str | None) -> list[AgeVerificationRequestView]:
        """운영자 심사 큐. status=None이면 전체."""
        ...

    async def transition(
        self,
        request_id: UUID,
        from_statuses: tuple[str, ...],
        to_status: str,
        operator_id: UUID,
        now: datetime,
    ) -> bool:
        """행 잠금 후 상태 전이 + id_photo_key를 NULL로(원본 삭제 반영). from_statuses 밖이면 False."""
        ...
