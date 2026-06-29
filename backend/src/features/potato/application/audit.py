"""감사 서비스 — 운영자 집행/변경 1건당 감사 1행 (누가·무엇을·대상·IP)."""
from typing import Protocol
from uuid import UUID


class AuditRepository(Protocol):
    async def record(
        self,
        operator_id: UUID,
        action: str,
        entity_type: str,
        entity_id: UUID | None = None,
        detail: dict | None = None,
        ip: str | None = None,
    ) -> None: ...


class AuditService:
    def __init__(self, repo: AuditRepository):
        self._repo = repo

    async def record(
        self,
        operator_id: UUID,
        action: str,
        entity_type: str,
        entity_id: UUID | None = None,
        detail: dict | None = None,
        ip: str | None = None,
    ) -> None:
        await self._repo.record(operator_id, action, entity_type, entity_id, detail, ip)
