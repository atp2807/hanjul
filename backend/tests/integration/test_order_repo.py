"""billing 통합 — 실 DB(SQLite)에서 주문→결제확인→정산 영속."""
from sqlalchemy import select

from src.features.auth.domain.models import SocialProfile
from src.features.auth.infrastructure.account_repo import SqlAccountRepository
from src.features.billing.application.order_service import OrderService
from src.features.billing.infrastructure.order_repo import SqlOrderRepository
from src.features.books.infrastructure.book_repo import SqlBookRepository
from src.infrastructure.db.models.order import Settlement
from tests.fixtures.fake_order_repo import FakeGateway


async def test_paid_order_persists_settlement(sessionmaker):
    # 사전: 구매자 account + 책 (FK 충족용 실 데이터)
    async with sessionmaker() as s:
        buyer = await SqlAccountRepository(s).create_with_credential(
            SocialProfile("GOOGLE", "buyer-1", "b@x.com", "구매자")
        )
        book_id = await SqlBookRepository(s).create_book(title="책", kind="BOOK", language="ko")

    # 주문 생성 + 결제확인 (Fake 게이트웨이로 검증 통과)
    async with sessionmaker() as s:
        svc = OrderService(SqlOrderRepository(s), FakeGateway(ok=True))
        order_id = await svc.create_order(book_id, buyer.id, 10000, "SELF")
        result = await svc.confirm_payment(order_id, "tx-1")
        assert result.payout_amt == 6769

    # 새 세션 — 주문 PAID + 정산 레코드 영속 확인
    async with sessionmaker() as s2:
        order = await SqlOrderRepository(s2).get_order(order_id)
        assert order.status_cd == "PAID"
        settlement = (
            await s2.execute(select(Settlement).where(Settlement.order_id == order_id))
        ).scalar_one()
        assert int(settlement.payout_amt) == 6769
        assert int(settlement.platform_fee_amt) == 3000
        assert int(settlement.withholding_amt) == 231
