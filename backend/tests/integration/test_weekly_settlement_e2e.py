"""매주 수요일 고정 정산 배치(lr-a0a8bda9) E2E — PayoutService.run_weekly_settlement.

환불세이프 게이트 자체(delivered_ts OR paid_ts+7일)는 이미 검증됨
(test_payout_refund_safe_gate_e2e.py). 여기는 배치 고유의 두 성질을 확인한다:
  (1) 계좌 등록된 작가만 환불세이프 미지급 정산이 payout으로 묶이고, 계좌 미등록 작가는
      스킵되어 정산분이 미지급인 채 남는지(다음 수요일 재시도 가능).
  (2) 같은 run_date로 재호출해도 settlement_run UNIQUE 멱등 가드 때문에 중복 payout이
      생기지 않는지, 다른 run_date면 다시 실행되는지.
"""
from datetime import UTC, date, datetime
from uuid import uuid4

from sqlalchemy import select
from src.features.payouts.application.payout_service import PayoutService
from src.features.payouts.domain.models import REQUESTED
from src.features.payouts.infrastructure.payout_repo import SqlPayoutRepository
from src.infrastructure.db.models.book import Book
from src.infrastructure.db.models.order import Order, Settlement
from src.infrastructure.db.models.payout import BankAccount, Payout, SettlementRun

RUN_DATE = date(2026, 7, 8)  # 실제 수요일 여부는 스케줄러가 판단 — 배치 자체는 받은 날짜로만 동작.


async def _seed_settlement(
    sessionmaker, author_id, *, paid_at, delivered_at=None, gross=7000, wh=231, payout=6769
):
    """작가의 PAID 판매 1건 + 정산(미지급) 시딩."""
    async with sessionmaker() as s:
        book = Book(
            title="책", kind="BOOK", language="ko", status="PUBLISHED",
            price_amt=10000, author_id=author_id,
        )
        s.add(book)
        await s.flush()
        order = Order(
            book_id=book.id, buyer_account_id=uuid4(), amount_amt=10000, channel="SELF",
            status="PAID", paid_at=paid_at, delivered_at=delivered_at,
        )
        s.add(order)
        await s.flush()
        s.add(Settlement(
            order_id=order.id, channel="SELF", gross_amt=gross, platform_fee_amt=3000,
            withholding_amt=wh, payout_amt=payout,
        ))
        await s.commit()


async def _seed_bank_account(sessionmaker, author_id):
    async with sessionmaker() as s:
        s.add(BankAccount(
            id=uuid4(), account_id=author_id, holder_name="작가", bank="004",
            account_no_enc="enc", account_no_masked="****7890", is_primary=True,
        ))
        await s.commit()


async def test_settles_author_with_bank_account_and_refund_safe_settlement(sessionmaker):
    """계좌 등록 + 환불세이프(delivered) 정산 → payout(REQUESTED) 1건 생성, settlement 묶임."""
    author_id = uuid4()
    await _seed_bank_account(sessionmaker, author_id)
    await _seed_settlement(sessionmaker, author_id, paid_at=datetime.now(UTC), delivered_at=datetime.now(UTC))

    async with sessionmaker() as s:
        count = await PayoutService(SqlPayoutRepository(s)).run_weekly_settlement(RUN_DATE)
    assert count == 1

    async with sessionmaker() as s:
        payouts = (await s.execute(select(Payout).where(Payout.author_id == author_id))).scalars().all()
        assert len(payouts) == 1
        assert payouts[0].status == REQUESTED
        assert int(payouts[0].net_amt) == 6769

        settled = (
            await s.execute(select(Settlement).where(Settlement.payout_id == payouts[0].id))
        ).scalars().all()
        assert len(settled) == 1


async def test_skips_author_without_bank_account(sessionmaker):
    """환불세이프 정산은 있지만 계좌 미등록 → payout 생성 안 됨, 정산분은 미지급으로 남음."""
    author_id = uuid4()
    await _seed_settlement(sessionmaker, author_id, paid_at=datetime.now(UTC), delivered_at=datetime.now(UTC))

    async with sessionmaker() as s:
        count = await PayoutService(SqlPayoutRepository(s)).run_weekly_settlement(RUN_DATE)
    assert count == 0

    async with sessionmaker() as s:
        payouts = (await s.execute(select(Payout).where(Payout.author_id == author_id))).scalars().all()
        assert payouts == []
        unpaid = (await s.execute(select(Settlement).where(Settlement.payout_id.is_(None)))).scalars().all()
        assert len(unpaid) == 1  # 다음 수요일 재시도 가능하도록 미지급 유지


async def test_excludes_non_refund_safe_settlement(sessionmaker):
    """계좌는 있어도 미delivered·결제 직후(변심철회 기간 안) 정산은 게이트에 막혀 스킵."""
    author_id = uuid4()
    await _seed_bank_account(sessionmaker, author_id)
    await _seed_settlement(sessionmaker, author_id, paid_at=datetime.now(UTC))  # delivered_at 없음

    async with sessionmaker() as s:
        count = await PayoutService(SqlPayoutRepository(s)).run_weekly_settlement(RUN_DATE)
    assert count == 0

    async with sessionmaker() as s:
        payouts = (await s.execute(select(Payout).where(Payout.author_id == author_id))).scalars().all()
        assert payouts == []


async def test_same_run_date_twice_is_idempotent(sessionmaker):
    """같은 run_date로 2회 호출 → 2회차는 claim 실패로 0건, 새로 생긴 정산분도 안 묶임(멱등)."""
    author_id = uuid4()
    await _seed_bank_account(sessionmaker, author_id)
    await _seed_settlement(sessionmaker, author_id, paid_at=datetime.now(UTC), delivered_at=datetime.now(UTC))

    async with sessionmaker() as s:
        first = await PayoutService(SqlPayoutRepository(s)).run_weekly_settlement(RUN_DATE)
    assert first == 1

    # 재호출 사이에 새 판매(환불세이프)가 생겨도 같은 run_date 재호출은 건드리면 안 됨.
    await _seed_settlement(
        sessionmaker, author_id, paid_at=datetime.now(UTC), delivered_at=datetime.now(UTC),
        gross=1000, wh=33, payout=967,
    )
    async with sessionmaker() as s:
        second = await PayoutService(SqlPayoutRepository(s)).run_weekly_settlement(RUN_DATE)
    assert second == 0

    async with sessionmaker() as s:
        payouts = (await s.execute(select(Payout).where(Payout.author_id == author_id))).scalars().all()
        assert len(payouts) == 1  # 재실행이 두 번째 payout을 만들지 않음(중복 payout 없음)

        runs = (await s.execute(select(SettlementRun).where(SettlementRun.run_date == RUN_DATE))).scalars().all()
        assert len(runs) == 1
        assert runs[0].payout_count == 1


async def test_different_run_date_executes_again(sessionmaker):
    """다른 run_date는 별개의 배치 — 새로 생긴 환불세이프 정산분을 또 정상적으로 묶는다."""
    author_id = uuid4()
    await _seed_bank_account(sessionmaker, author_id)
    await _seed_settlement(sessionmaker, author_id, paid_at=datetime.now(UTC), delivered_at=datetime.now(UTC))

    async with sessionmaker() as s:
        first = await PayoutService(SqlPayoutRepository(s)).run_weekly_settlement(RUN_DATE)
    assert first == 1

    other_run_date = date(2026, 7, 15)
    await _seed_settlement(
        sessionmaker, author_id, paid_at=datetime.now(UTC), delivered_at=datetime.now(UTC),
        gross=1000, wh=33, payout=967,
    )
    async with sessionmaker() as s:
        second = await PayoutService(SqlPayoutRepository(s)).run_weekly_settlement(other_run_date)
    assert second == 1

    async with sessionmaker() as s:
        payouts = (await s.execute(select(Payout).where(Payout.author_id == author_id))).scalars().all()
        assert len(payouts) == 2
