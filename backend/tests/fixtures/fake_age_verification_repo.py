"""인메모리 AgeVerificationRepository — 서비스 단위 테스트용.

Protocol 구현 대상: src.features.age_verification.domain.models.AgeVerificationRepository
  (get_pending_for_account · create_request · get_request · list_by_status · transition)

⚠️ get_*/list_* 는 반드시 dataclasses.replace로 복사본을 반환한다(실 SqlAgeVerificationRepository가
ORM row에서 매번 새 dataclass를 만드는 것과 동일한 시맨틱) — 저장된 원본 참조를 그대로 주면,
서비스가 들고 있는 뷰가 이후 transition()의 인플레이스 변경(id_photo_key=None 등)에 의해
호출자 모르게 바뀌어버려 "심사 전 값 캡처 후 삭제" 로직을 검증할 수 없게 된다.
"""
import uuid
from dataclasses import replace
from uuid import UUID

from src.features.age_verification.domain.models import PENDING, AgeVerificationRequestView


class FakeAgeVerificationRepository:
    def __init__(self) -> None:
        self.requests: dict[UUID, AgeVerificationRequestView] = {}

    def seed(self, view: AgeVerificationRequestView) -> None:
        self.requests[view.id] = view

    async def get_pending_for_account(self, account_id: UUID) -> AgeVerificationRequestView | None:
        for r in self.requests.values():
            if r.account_id == account_id and r.status == PENDING:
                return replace(r)
        return None

    async def create_request(self, account_id: UUID, id_photo_key: str) -> AgeVerificationRequestView:
        from datetime import UTC, datetime

        view = AgeVerificationRequestView(
            id=uuid.uuid4(), account_id=account_id, status=PENDING,
            id_photo_key=id_photo_key, created_at=datetime.now(UTC),
        )
        self.requests[view.id] = view
        return replace(view)

    async def get_request(self, request_id: UUID) -> AgeVerificationRequestView | None:
        r = self.requests.get(request_id)
        return replace(r) if r is not None else None

    async def list_by_status(self, status: str | None) -> list[AgeVerificationRequestView]:
        rows = self.requests.values()
        if status is not None:
            rows = [r for r in rows if r.status == status]
        return [replace(r) for r in rows]

    async def transition(self, request_id, from_statuses, to_status, operator_id, now) -> bool:
        r = self.requests.get(request_id)
        if r is None or r.status not in from_statuses:
            return False
        r.status = to_status
        r.reviewed_by = operator_id
        r.reviewed_at = now
        r.id_photo_key = None  # 심사완료 즉시 원본 참조 제거(실 SqlAgeVerificationRepository와 동일)
        return True
