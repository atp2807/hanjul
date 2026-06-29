"""potato.audit_log SQL 어댑터 — 운영자 행위 감사."""
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.db.models.operator import AuditLog


class SqlAuditRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def record(
        self,
        operator_id: UUID,
        action: str,
        entity_type: str,
        entity_id: UUID | None = None,
        detail: dict | None = None,
        ip: str | None = None,
    ) -> None:
        self.session.add(
            AuditLog(
                id=uuid4(),
                operator_id=operator_id,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                detail=detail,
                ip=ip,
            )
        )
        await self.session.commit()
