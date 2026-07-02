"""payouts SQLAlchemy 어댑터 — bill.bank_account / bill.payout / settlement 집계."""
from uuid import UUID, uuid4

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.features.payouts.domain.models import (
    REQUESTED,
    BankAccountView,
    PayableSummary,
    PayoutView,
)
from src.infrastructure.db.models.book import Book
from src.infrastructure.db.models.order import Order, Settlement
from src.infrastructure.db.models.payout import BankAccount, Payout


def _acct_view(a: BankAccount) -> BankAccountView:
    return BankAccountView(
        id=a.id, holder_name=a.holder_name, bank=a.bank, account_no_masked=a.account_no_masked
    )


def _payout_view(p: Payout) -> PayoutView:
    return PayoutView(
        id=p.id, author_id=p.author_id, status=p.status,
        gross_amt=int(p.gross_amt), withholding_amt=int(p.withholding_amt), net_amt=int(p.net_amt),
        holder_name=p.holder_name, bank=p.bank, account_no_masked=p.account_no_masked,
        requested_at=p.requested_at, approved_at=p.approved_at, paid_at=p.paid_at, memo=p.memo,
    )


class SqlPayoutRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    # ── 계좌 ──────────────────────────────────────────
    async def get_bank_account(self, account_id: UUID) -> BankAccountView | None:
        row = (
            await self.session.execute(
                select(BankAccount).where(BankAccount.account_id == account_id, BankAccount.primary_yn.is_(True))
            )
        ).scalar_one_or_none()
        return _acct_view(row) if row else None

    async def upsert_bank_account(
        self, account_id, holder_name, bank, account_no_enc, account_no_masked
    ) -> BankAccountView:
        row = (
            await self.session.execute(
                select(BankAccount).where(BankAccount.account_id == account_id, BankAccount.primary_yn.is_(True))
            )
        ).scalar_one_or_none()
        if row is None:
            row = BankAccount(
                id=uuid4(), account_id=account_id, holder_name=holder_name, bank=bank,
                account_no_enc=account_no_enc, account_no_masked=account_no_masked, primary_yn=True,
            )
            self.session.add(row)
        else:
            row.holder_name, row.bank = holder_name, bank
            row.account_no_enc, row.account_no_masked = account_no_enc, account_no_masked
        await self.session.commit()
        await self.session.refresh(row)
        return _acct_view(row)

    # ── 미지급 정산 집계 ──────────────────────────────
    def _unpaid_stmt(self, author_id: UUID):
        return (
            select(Settlement)
            .join(Order, Order.id == Settlement.order_id)
            .join(Book, Book.id == Order.book_id)
            .where(
                Book.author_id == author_id,
                Order.status == "PAID",
                Order.channel != "REVIEW",
                Settlement.payout_id.is_(None),
            )
        )

    async def payable_summary(self, author_id: UUID) -> PayableSummary:
        row = (
            await self.session.execute(
                select(
                    func.coalesce(func.sum(Settlement.gross_amt), 0),
                    func.coalesce(func.sum(Settlement.withholding_amt), 0),
                    func.coalesce(func.sum(Settlement.payout_amt), 0),
                    func.count(Settlement.id),
                )
                .select_from(Settlement)
                .join(Order, Order.id == Settlement.order_id)
                .join(Book, Book.id == Order.book_id)
                .where(
                    Book.author_id == author_id,
                    Order.status == "PAID",
                    Order.channel != "REVIEW",
                    Settlement.payout_id.is_(None),
                )
            )
        ).one()
        return PayableSummary(
            gross_amt=int(row[0]), withholding_amt=int(row[1]), net_amt=int(row[2]), order_count=int(row[3])
        )

    async def create_payout(self, author_id: UUID, account: BankAccountView) -> PayoutView | None:
        rows = (await self.session.execute(self._unpaid_stmt(author_id))).scalars().all()
        if not rows:
            return None
        gross = sum(int(s.gross_amt) for s in rows)
        withholding = sum(int(s.withholding_amt) for s in rows)
        net = sum(int(s.payout_amt) for s in rows)
        payout = Payout(
            id=uuid4(), author_id=author_id, status=REQUESTED,
            gross_amt=gross, withholding_amt=withholding, net_amt=net,
            holder_name=account.holder_name, bank=account.bank, account_no_masked=account.account_no_masked,
        )
        self.session.add(payout)
        await self.session.flush()
        for s in rows:
            s.payout_id = payout.id
        await self.session.commit()
        await self.session.refresh(payout)
        return _payout_view(payout)

    # ── 조회 ──────────────────────────────────────────
    async def list_payouts(self, author_id: UUID) -> list[PayoutView]:
        rows = (
            await self.session.execute(
                select(Payout).where(Payout.author_id == author_id).order_by(Payout.requested_at.desc())
            )
        ).scalars().all()
        return [_payout_view(p) for p in rows]

    async def get_payout(self, payout_id: UUID) -> PayoutView | None:
        p = await self.session.get(Payout, payout_id)
        return _payout_view(p) if p else None

    async def list_by_status(self, status: str | None) -> list[PayoutView]:
        stmt = select(Payout)
        if status:
            stmt = stmt.where(Payout.status == status)
        stmt = stmt.order_by(Payout.requested_at.asc())
        rows = (await self.session.execute(stmt)).scalars().all()
        return [_payout_view(p) for p in rows]

    async def set_status(self, payout_id, status, operator_id, now, memo=None) -> None:
        p = await self.session.get(Payout, payout_id)
        p.status = status
        if memo is not None:
            p.memo = memo
        if status == "APPROVED":
            p.approved_at, p.approved_by = now, operator_id
        elif status == "PAID":
            p.paid_at = now
            if p.approved_by is None:
                p.approved_by = operator_id
        await self.session.commit()

    async def unlink_settlements(self, payout_id: UUID) -> None:
        await self.session.execute(
            update(Settlement).where(Settlement.payout_id == payout_id).values(payout_id=None)
        )
        await self.session.commit()
