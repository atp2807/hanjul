"""billing 통합 — 실 DB(SQLite)에서 출판본 구매→결제확인→정산 영속."""
from datetime import UTC, datetime

from sqlalchemy import select
from src.features.auth.domain.models import SocialProfile
from src.features.auth.infrastructure.account_repo import SqlAccountRepository
from src.features.billing.application.order_service import OrderService
from src.features.billing.infrastructure.book_pricing import SqlBookPricing
from src.features.billing.infrastructure.order_repo import SqlOrderRepository
from src.features.books.infrastructure.book_repo import SqlBookRepository
from src.features.catalog.infrastructure.catalog_repo import SqlCatalogRepository
from src.infrastructure.db.models.order import Settlement

from tests.fixtures.fake_order_repo import FakeGateway


async def test_paid_order_persists_settlement(sessionmaker):
    # 사전: 구매자 + 출판본(가격 10000)
    async with sessionmaker() as s:
        buyer = await SqlAccountRepository(s).create_with_credential(
            SocialProfile("GOOGLE", "buyer-1", "b@x.com", "구매자")
        )
        book_id = await SqlBookRepository(s).create_book(title="책", kind="BOOK", language="ko")
        cat = SqlCatalogRepository(s)
        await cat.set_price(book_id, 10000)
        await cat.set_status(book_id, "PUBLISHED", datetime.now(UTC))

    # 구매 (금액은 서버가 가격에서 도출) + 결제확인
    async with sessionmaker() as s:
        svc = OrderService(SqlOrderRepository(s), FakeGateway(ok=True), SqlBookPricing(s))
        order_id = await svc.create_order(book_id, buyer.id, "SELF", withdrawal_consent=True)
        result = await svc.confirm_payment(order_id, "tx-1")
        assert result.payout_amt == 6769

    # 영속 확인
    async with sessionmaker() as s2:
        order = await SqlOrderRepository(s2).get_order(order_id)
        assert order.status == "PAID"
        assert order.amount_amt == 10000  # 서버 가격
        settlement = (
            await s2.execute(select(Settlement).where(Settlement.order_id == order_id))
        ).scalar_one()
        assert int(settlement.payout_amt) == 6769
        assert int(settlement.platform_fee_amt) == 3000
        assert int(settlement.withholding_amt) == 231
