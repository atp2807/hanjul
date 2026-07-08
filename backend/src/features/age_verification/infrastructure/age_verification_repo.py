"""AgeVerificationRepository의 SQLAlchemy 구현 — usr.age_verification_request."""
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.features.age_verification.domain.models import PENDING, AgeVerificationRequestView
from src.infrastructure.db.models.age_verification import AgeVerificationRequest


def _to_view(r: AgeVerificationRequest) -> AgeVerificationRequestView:
    return AgeVerificationRequestView(
        id=r.id,
        account_id=r.account_id,
        status=r.status,
        id_photo_key=r.id_photo_key,
        created_at=r.created_at,
        reviewed_at=r.reviewed_at,
        reviewed_by=r.reviewed_by,
    )


class SqlAgeVerificationRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_pending_for_account(self, account_id: UUID) -> AgeVerificationRequestView | None:
        row = (
            await self.session.execute(
                select(AgeVerificationRequest).where(
                    AgeVerificationRequest.account_id == account_id,
                    AgeVerificationRequest.status == PENDING,
                )
            )
        ).scalar_one_or_none()
        return _to_view(row) if row else None

    async def create_request(self, account_id: UUID, id_photo_key: str) -> AgeVerificationRequestView:
        row = AgeVerificationRequest(
            id=uuid4(), account_id=account_id, id_photo_key=id_photo_key, status=PENDING
        )
        self.session.add(row)
        await self.session.commit()
        await self.session.refresh(row)
        return _to_view(row)

    async def get_request(self, request_id: UUID) -> AgeVerificationRequestView | None:
        row = await self.session.get(AgeVerificationRequest, request_id)
        return _to_view(row) if row else None

    async def list_by_status(self, status: str | None) -> list[AgeVerificationRequestView]:
        stmt = select(AgeVerificationRequest)
        if status:
            stmt = stmt.where(AgeVerificationRequest.status == status)
        stmt = stmt.order_by(AgeVerificationRequest.created_at.asc())
        rows = (await self.session.execute(stmt)).scalars().all()
        return [_to_view(r) for r in rows]

    async def transition(
        self, request_id: UUID, from_statuses: tuple[str, ...], to_status: str, operator_id: UUID, now
    ) -> bool:
        # 행 잠금 후 현재 상태 재확인 — 운영자 둘이 동시에 승인/거부해도 한 명만 성공(payout 패턴과 동일).
        row = (
            await self.session.execute(
                select(AgeVerificationRequest)
                .where(AgeVerificationRequest.id == request_id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
        ).scalar_one_or_none()
        if row is None or row.status not in from_statuses:
            await self.session.rollback()
            return False
        row.status = to_status
        row.reviewed_by = operator_id
        row.reviewed_at = now
        row.id_photo_key = None  # 심사완료 즉시 원본 참조 제거 (실제 파일삭제는 서비스가 별도 수행)
        await self.session.commit()
        return True
