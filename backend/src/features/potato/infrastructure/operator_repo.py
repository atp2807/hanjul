"""potato.operator SQL 어댑터."""
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.features.potato.domain.models import Operator
from src.infrastructure.db.models.operator import Operator as OperatorRow


class SqlOperatorRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def _to_domain(row: OperatorRow) -> Operator:
        return Operator(
            id=row.id,
            email=row.email,
            name=row.name,
            role=row.role,
            is_active=row.is_active,
            password_hash=row.password_hash,
        )

    async def get_by_email(self, email: str) -> Operator | None:
        row = (
            await self.session.execute(select(OperatorRow).where(OperatorRow.email == email))
        ).scalar_one_or_none()
        return self._to_domain(row) if row else None

    async def get(self, operator_id: UUID) -> Operator | None:
        row = await self.session.get(OperatorRow, operator_id)
        return self._to_domain(row) if row else None

    async def create(
        self, email: str, name: str, role: str, password_hash: str
    ) -> Operator:
        row = OperatorRow(
            id=uuid4(),
            email=email,
            name=name,
            role=role,
            password_hash=password_hash,
            is_active=True,
        )
        self.session.add(row)
        await self.session.commit()
        await self.session.refresh(row)
        return self._to_domain(row)
