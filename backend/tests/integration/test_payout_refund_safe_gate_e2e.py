"""환불세이프 게이트(payout_repo._unpaid_stmt, lr-6b6f01e3) — 실 DB(SQLite) 통합테스트.

배경: 전자책은 오픈되면 청약철회 제한(전자상거래법 §17①/②)이라 그 판매는 확정 → 출금해도
안전. 그래서 출금가능액(payable)·출금생성(create_payout) 둘 다 "환불세이프" 주문의 정산분만
포함한다. 환불세이프 = delivered_ts 존재(전자책 제공 개시) OR paid_ts 후 7일 경과(일반 변심
철회 기간 종료). payable_summary와 create_payout은 같은 _unpaid_stmt를 쓰므로 이 파일은
주로 payable_summary로 게이트 조건을 검증하고, 마지막에 create_payout도 같은 게이트를
따른다는 것을 별도로 확인한다(표시뿐 아니라 실지급도 막혀야 한다는 게 이 기능의 핵심).
"""
import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from src.features.billing.infrastructure.order_repo import SqlOrderRepository
from src.features.payouts.domain.models import BankAccountView
from src.features.payouts.infrastructure.payout_repo import SqlPayoutRepository
from src.infrastructure.db.models.book import Book
from src.infrastructure.db.models.order import Order, Settlement


async def _seed(sessionmaker, author_id, *, paid_at, delivered_at=None, gross=7000, wh=231, payout=6769):
    """작가의 PAID 판매 1건 + 정산(미지급) 시딩 — paid_at/delivered_at을 테스트가 직접 제어.

    반환: (order_id, book_id, buyer_id) — mark_delivered 등 후속 조작에 필요.
    """
    buyer_id = uuid4()
    async with sessionmaker() as s:
        book = Book(
            title="책", kind="BOOK", language="ko", status="PUBLISHED",
            price_amt=10000, author_id=author_id,
        )
        s.add(book)
        await s.flush()
        order = Order(
            book_id=book.id, buyer_account_id=buyer_id, amount_amt=10000, channel="SELF",
            status="PAID", paid_at=paid_at, delivered_at=delivered_at,
        )
        s.add(order)
        await s.flush()
        s.add(Settlement(
            order_id=order.id, channel="SELF", gross_amt=gross, platform_fee_amt=3000,
            withholding_amt=wh, payout_amt=payout,
        ))
        await s.commit()
        return order.id, book.id, buyer_id


async def test_delivered_order_is_payable(sessionmaker):
    """(a) delivered된 주문 — 결제된 지 얼마 안 됐어도 출금 가능(제공 개시로 청약철회 제한 발동)."""
    author_id = uuid4()
    await _seed(sessionmaker, author_id, paid_at=datetime.now(UTC), delivered_at=datetime.now(UTC))

    async with sessionmaker() as s:
        summary = await SqlPayoutRepository(s).payable_summary(author_id)
    assert summary.order_count == 1
    assert summary.net_amt == 6769


async def test_undelivered_recent_order_excluded(sessionmaker):
    """(b) 미delivered·결제 직후 — 아직 변심철회 기간 안이라 출금 불가."""
    author_id = uuid4()
    await _seed(sessionmaker, author_id, paid_at=datetime.now(UTC))

    async with sessionmaker() as s:
        summary = await SqlPayoutRepository(s).payable_summary(author_id)
    assert summary.order_count == 0
    assert summary.net_amt == 0


async def test_undelivered_old_order_included(sessionmaker):
    """(c) 미delivered·결제 후 7일 초과(백데이트) — 변심철회 기간이 끝나 출금 가능."""
    author_id = uuid4()
    await _seed(sessionmaker, author_id, paid_at=datetime.now(UTC) - timedelta(days=8))

    async with sessionmaker() as s:
        summary = await SqlPayoutRepository(s).payable_summary(author_id)
    assert summary.order_count == 1
    assert summary.net_amt == 6769


async def test_undelivered_order_just_under_7_days_excluded(sessionmaker):
    """경계값 — 6일 23시간 전 결제는 아직 7일이 안 지나 게이트에 막힌다."""
    author_id = uuid4()
    await _seed(sessionmaker, author_id, paid_at=datetime.now(UTC) - timedelta(days=6, hours=23))

    async with sessionmaker() as s:
        summary = await SqlPayoutRepository(s).payable_summary(author_id)
    assert summary.order_count == 0


async def test_mark_delivered_is_idempotent(sessionmaker):
    """(d) mark_delivered 2회 호출해도 delivered_ts는 최초 1회 값 그대로."""
    author_id = uuid4()
    order_id, book_id, buyer_id = await _seed(sessionmaker, author_id, paid_at=datetime.now(UTC))

    async with sessionmaker() as s:
        await SqlOrderRepository(s).mark_delivered(buyer_id, book_id)
    async with sessionmaker() as s:
        order = await s.get(Order, order_id)
        first_delivered_at = order.delivered_at
        assert first_delivered_at is not None

    await asyncio.sleep(0.01)  # 재호출 시각이 달라질 여지를 둬도 값이 안 바뀌어야 멱등 증명이 됨
    async with sessionmaker() as s:
        await SqlOrderRepository(s).mark_delivered(buyer_id, book_id)
    async with sessionmaker() as s:
        order = await s.get(Order, order_id)
        assert order.delivered_at == first_delivered_at


async def test_create_payout_only_sweeps_refund_safe_settlements(sessionmaker):
    """실지급 생성(create_payout)도 payable_summary와 같은 게이트를 탄다 — 표시뿐 아니라
    실제 출금(payout)에도 미delivered·7일 이내 정산분은 절대 안 묶여야 한다."""
    author_id = uuid4()
    # 환불세이프(delivered) 정산 1건 + 아직 변심철회 기간 안인 정산 1건 — 같은 작가.
    await _seed(sessionmaker, author_id, paid_at=datetime.now(UTC), delivered_at=datetime.now(UTC),
                gross=7000, wh=231, payout=6769)
    await _seed(sessionmaker, author_id, paid_at=datetime.now(UTC), gross=3500, wh=115, payout=3385)

    account = BankAccountView(id=uuid4(), holder_name="작가", bank="004", account_no_masked="****7890")
    async with sessionmaker() as s:
        payout_view = await SqlPayoutRepository(s).create_payout(author_id, account)
    assert payout_view is not None
    assert payout_view.net_amt == 6769  # delivered 건만 묶임, 미delivered 건은 제외

    # 남은 미delivered 건은 여전히 출금 불가로 남아있어야(사라지거나 잘못 묶이지 않음).
    async with sessionmaker() as s:
        summary = await SqlPayoutRepository(s).payable_summary(author_id)
    assert summary.order_count == 0
    assert summary.net_amt == 0
