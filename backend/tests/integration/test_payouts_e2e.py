"""작가 출금 인프라 E2E — 계좌등록 → 판매 → 출금가능액 → 신청 → 운영자 승인·지급."""
from datetime import datetime, timezone
from uuid import UUID, uuid4

import httpx
import pytest
from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import settings

settings.DEBUG = False

from main import app  # noqa: E402
from src.config.database import get_potato_session, get_session  # noqa: E402
from src.features.auth.application.auth_service import AuthService  # noqa: E402
from src.features.auth.domain.models import SocialProfile  # noqa: E402
from src.features.auth.infrastructure.account_repo import SqlAccountRepository  # noqa: E402
from src.features.auth.presentation.dependencies import get_auth_service, token_issuer  # noqa: E402
from src.features.payouts.application.crypto import decrypt  # noqa: E402
from src.features.potato.application.password import hash_password  # noqa: E402
from src.features.potato.domain.models import OPERATOR  # noqa: E402
from src.features.potato.infrastructure.operator_repo import SqlOperatorRepository  # noqa: E402
from src.infrastructure.db.models.book import Book  # noqa: E402
from src.infrastructure.db.models.order import Order, Settlement  # noqa: E402
from src.infrastructure.db.models.payout import BankAccount, Payout  # noqa: E402
from tests.fixtures.fake_account_repo import FakeProvider  # noqa: E402
from tests.integration.auth_helpers import login_account  # noqa: E402

AUTHOR = SocialProfile("GOOGLE", "author-sub", "author@x.com", "작가")
OP_EMAIL, OP_PW = "payop@hanjul.io", "potato-pay-123"


@pytest.fixture
def app_db(sessionmaker):
    async def _session():
        async with sessionmaker() as s:
            yield s

    def _auth(session: AsyncSession = Depends(get_session)):
        return AuthService(
            SqlAccountRepository(session), {"GOOGLE": FakeProvider("GOOGLE", AUTHOR)}, token_issuer()
        )

    app.dependency_overrides[get_session] = _session
    app.dependency_overrides[get_potato_session] = _session
    app.dependency_overrides[get_auth_service] = _auth
    yield sessionmaker
    app.dependency_overrides.clear()


def _client():
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app, client=("127.0.0.1", 50000)), base_url="http://t"
    )


async def _seed_sale(sessionmaker, author_id, gross=7000, wh=231, payout=6769) -> None:
    """작가의 PAID 판매 1건 + 정산 스냅샷(미지급)."""
    author_id = UUID(author_id) if isinstance(author_id, str) else author_id
    async with sessionmaker() as s:
        book = Book(title="책", kind="BOOK", language="ko", status="PUBLISHED", price_amt=10000, author_id=author_id)
        s.add(book)
        await s.flush()
        order = Order(book_id=book.id, buyer_account_id=uuid4(), amount_amt=10000, channel="SELF",
                      status="PAID", paid_at=datetime.now(timezone.utc))
        s.add(order)
        await s.flush()
        s.add(Settlement(order_id=order.id, channel="SELF", gross_amt=gross, platform_fee_amt=3000,
                         withholding_amt=wh, payout_amt=payout))
        await s.commit()


async def _op_token(c, sessionmaker) -> str:
    async with sessionmaker() as s:
        await SqlOperatorRepository(s).create(email=OP_EMAIL, name="운영자", role=OPERATOR,
                                              password_hash=hash_password(OP_PW))
    r = await c.post("/api/potato/auth/login", json={"email": OP_EMAIL, "password": OP_PW})
    return r.json()["token"]


async def test_full_payout_lifecycle(app_db):
    async with _client() as c:
        token, acc = await login_account(c, "google", "x")
        hdr = {"Authorization": f"Bearer {token}"}
        author_id = acc["id"]

        # 계좌 미등록 → 출금 신청 422
        await _seed_sale(app_db, author_id)
        assert (await c.post("/api/me/payouts", headers=hdr)).status_code == 422

        # 계좌 등록 (계좌번호 암호화 저장 확인)
        r = await c.put("/api/me/bank-account", headers=hdr,
                        json={"holderName": "작가", "bank": "004", "accountNo": "123-456-7890"})
        assert r.status_code == 200, r.text
        assert r.json()["accountNoMasked"].endswith("7890")
        assert "123" not in r.json()["accountNoMasked"]  # 마스킹됨

        # 출금 가능액 = 미지급 정산 payout_amt 합
        payable = (await c.get("/api/me/payouts/payable", headers=hdr)).json()
        assert payable["netAmt"] == 6769
        assert payable["orderCount"] == 1

        # 출금 신청
        req = await c.post("/api/me/payouts", headers=hdr)
        assert req.status_code == 201, req.text
        payout_id = req.json()["id"]
        assert req.json()["status"] == "REQUESTED"
        assert req.json()["netAmt"] == 6769

        # 신청 후 출금가능액 0 (정산분이 payout에 묶임)
        assert (await c.get("/api/me/payouts/payable", headers=hdr)).json()["netAmt"] == 0

        # 개인정보 export 에 판매·계좌(마스킹)·출금내역 포함 (§35 열람권 일괄)
        exp = (await c.get("/api/me/export", headers=hdr)).json()
        assert exp["bankAccount"]["accountNoMasked"].endswith("7890")
        assert exp["payouts"][0]["id"] == payout_id
        assert exp["sales"]["totalRevenue"] == 10000

        # DB: 계좌번호 복호화되고 settlement가 payout에 묶임
        async with app_db() as s:
            ba = (await s.execute(select(BankAccount))).scalar_one()
            assert decrypt(ba.account_no_enc) == "1234567890"
            st = (await s.execute(select(Settlement))).scalar_one()
            assert str(st.payout_id) == payout_id

        # 운영자: 승인 → 지급완료
        op_hdr = {"Authorization": f"Bearer {await _op_token(c, app_db)}"}
        queue = (await c.get("/api/potato/payouts", headers=op_hdr)).json()
        assert any(p["id"] == payout_id for p in queue)
        assert (await c.post(f"/api/potato/payouts/{payout_id}/approve", headers=op_hdr)).status_code == 204
        assert (await c.post(f"/api/potato/payouts/{payout_id}/pay", headers=op_hdr,
                             json={"reason": "이체완료"})).status_code == 204

        # 최종 상태 PAID
        async with app_db() as s:
            p = (await s.execute(select(Payout))).scalar_one()
            assert p.status == "PAID"
            assert p.paid_at is not None


async def test_reject_returns_funds(app_db):
    async with _client() as c:
        token, acc = await login_account(c, "google", "x")
        hdr = {"Authorization": f"Bearer {token}"}
        await _seed_sale(app_db, acc["id"])
        await c.put("/api/me/bank-account", headers=hdr,
                    json={"holderName": "작가", "bank": "004", "accountNo": "1234567890"})
        payout_id = (await c.post("/api/me/payouts", headers=hdr)).json()["id"]

        op_hdr = {"Authorization": f"Bearer {await _op_token(c, app_db)}"}
        # 반려 → 정산분 회수 → 다시 출금 가능
        assert (await c.post(f"/api/potato/payouts/{payout_id}/reject", headers=op_hdr,
                             json={"reason": "계좌오류"})).status_code == 204
        assert (await c.get("/api/me/payouts/payable", headers=hdr)).json()["netAmt"] == 6769


async def test_payout_state_machine_guards(app_db):
    """상태기계 회귀 가드 — 중복 승인/조기 지급/지급 후 반려는 전부 409.

    repo.transition 이 행 잠금 + 현재 상태 재확인으로 전이하므로
    운영자 둘이 동시에 눌러도 한 명만 성공한다 (여기선 순차 재현).
    """
    async with _client() as c:
        token, acc = await login_account(c, "google", "x")
        hdr = {"Authorization": f"Bearer {token}"}
        await _seed_sale(app_db, acc["id"])
        await c.put("/api/me/bank-account", headers=hdr,
                    json={"holderName": "작가", "bank": "004", "accountNo": "1234567890"})
        payout_id = (await c.post("/api/me/payouts", headers=hdr)).json()["id"]
        op_hdr = {"Authorization": f"Bearer {await _op_token(c, app_db)}"}

        # 승인 전 지급 → 409
        assert (await c.post(f"/api/potato/payouts/{payout_id}/pay", headers=op_hdr,
                             json={"reason": "x"})).status_code == 409
        assert (await c.post(f"/api/potato/payouts/{payout_id}/approve", headers=op_hdr)).status_code == 204
        # 중복 승인 → 409 (두 번째 운영자)
        assert (await c.post(f"/api/potato/payouts/{payout_id}/approve", headers=op_hdr)).status_code == 409
        assert (await c.post(f"/api/potato/payouts/{payout_id}/pay", headers=op_hdr,
                             json={"reason": "이체완료"})).status_code == 204
        # 지급 후 반려 → 409 (정산 회수 불가)
        assert (await c.post(f"/api/potato/payouts/{payout_id}/reject", headers=op_hdr,
                             json={"reason": "x"})).status_code == 409
        assert (await c.get("/api/me/payouts/payable", headers=hdr)).json()["netAmt"] == 0


async def test_payout_requires_auth_and_operator(app_db):
    async with _client() as c:
        assert (await c.get("/api/me/payouts/payable")).status_code == 401
        # 고객 토큰으로 운영자 출금목록 → 401(방화벽)
        token, _ = await login_account(c, "google", "x")
        assert (
            await c.get("/api/potato/payouts", headers={"Authorization": f"Bearer {token}"})
        ).status_code == 401
