"""woncheon 원천징수 신고 커넥터 E2E (lr-ac61f505 스켈레톤).

주민번호 등록(최소수집) → PAID 전이 → best-effort 신고 시도(미설정이라 보류) → PAID 상태는
그대로 유지 → potato 미신고 목록에 노출. ⚠️ WONCHEON_API_BASE/KEY 를 명시적으로 비워
(monkeypatch) 실 네트워크 호출이 절대 일어나지 않게 보장한 채로 검증한다.
"""
from datetime import UTC, datetime
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
from src.infrastructure.db.models.payout import Payout  # noqa: E402
from src.infrastructure.db.models.withholding import WithholdingSubject  # noqa: E402

from tests.fixtures.fake_account_repo import FakeProvider  # noqa: E402
from tests.integration.auth_helpers import login_account  # noqa: E402

AUTHOR = SocialProfile("GOOGLE", "wc-author-sub", "wc-author@x.com", "작가")
OP_EMAIL, OP_PW = "wcop@hanjul.io", "potato-wc-123"
RESIDENT_NO = "9001011234567"


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


@pytest.fixture(autouse=True)
def _woncheon_unconfigured(monkeypatch):
    """이 스켈레톤 단계에선 실 테넌트 미등록 — 설정을 명시적으로 비워 네트워크 호출을 원천 차단."""
    monkeypatch.setattr(settings, "WONCHEON_API_BASE", "")
    monkeypatch.setattr(settings, "WONCHEON_API_KEY", "")
    monkeypatch.setattr(settings, "WONCHEON_DEFAULT_INCOME_TYPE_CODE", "940906")


def _client():
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app, client=("127.0.0.1", 50001)), base_url="http://t"
    )


async def _seed_sale(sessionmaker, author_id, gross=7000, wh=231, payout=6769) -> None:
    author_id = UUID(author_id) if isinstance(author_id, str) else author_id
    async with sessionmaker() as s:
        book = Book(title="책", kind="BOOK", language="ko", status="PUBLISHED", price_amt=10000, author_id=author_id)
        s.add(book)
        await s.flush()
        order = Order(book_id=book.id, buyer_account_id=uuid4(), amount_amt=10000, channel="SELF",
                      status="PAID", paid_at=datetime.now(UTC))
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


async def test_paid_transition_holds_report_when_subject_registered_but_unconfigured(app_db):
    """주민번호 등록 후 PAID 전이 — best-effort 신고는 (미설정이라) 보류되지만 PAID 자체는 유지."""
    async with _client() as c:
        token, acc = await login_account(c, "google", "x")
        hdr = {"Authorization": f"Bearer {token}"}
        author_id = acc["id"]
        await _seed_sale(app_db, author_id)
        await c.put("/api/me/bank-account", headers=hdr,
                    json={"holderName": "작가", "bank": "004", "accountNo": "1234567890"})
        payout_id = (await c.post("/api/me/payouts", headers=hdr)).json()["id"]

        op_hdr = {"Authorization": f"Bearer {await _op_token(c, app_db)}"}
        assert (await c.post(f"/api/potato/payouts/{payout_id}/approve", headers=op_hdr)).status_code == 204

        # 주민번호 최소수집 등록 (계좌등록과 별개 테이블)
        r = await c.put(
            f"/api/potato/payouts/{payout_id}/withholding-subject", headers=op_hdr,
            json={"residentNumber": RESIDENT_NO},
        )
        assert r.status_code == 204, r.text

        # PAID 전이 — 훅이 best-effort로 신고 시도하지만 미설정이라 실패해도 지급 자체는 확정됨
        r = await c.post(f"/api/potato/payouts/{payout_id}/pay", headers=op_hdr, json={"reason": "이체완료"})
        assert r.status_code == 204, r.text

        async with app_db() as s:
            p = (await s.execute(select(Payout).where(Payout.id == UUID(payout_id)))).scalar_one()
            assert p.status == "PAID"  # 신고 실패와 무관하게 지급은 확정
            assert p.woncheon_reported_at is None  # 미설정이라 신고는 안 됨(보류) — 재시도 대상

            subj = (
                await s.execute(select(WithholdingSubject).where(WithholdingSubject.payout_id == UUID(payout_id)))
            ).scalar_one()
            assert decrypt(subj.resident_no_enc) == RESIDENT_NO  # 암호화 저장 확인
            assert subj.income_type_code == "940906"

        # potato 미신고 목록에 노출 (has_subject=True — 주민번호는 있는데 신고만 안 됨)
        unreported = (await c.get("/api/potato/payouts/woncheon/unreported", headers=op_hdr)).json()
        row = next(x for x in unreported if x["payoutId"] == payout_id)
        assert row["hasSubject"] is True


async def test_paid_transition_succeeds_even_without_subject_registered(app_db):
    """주민번호를 아예 등록 안 해도 PAID 전이는 정상 — 신고는 완전히 보류될 뿐."""
    async with _client() as c:
        token, acc = await login_account(c, "google", "x")
        hdr = {"Authorization": f"Bearer {token}"}
        await _seed_sale(app_db, acc["id"])
        await c.put("/api/me/bank-account", headers=hdr,
                    json={"holderName": "작가", "bank": "004", "accountNo": "1234567890"})
        payout_id = (await c.post("/api/me/payouts", headers=hdr)).json()["id"]

        op_hdr = {"Authorization": f"Bearer {await _op_token(c, app_db)}"}
        await c.post(f"/api/potato/payouts/{payout_id}/approve", headers=op_hdr)

        r = await c.post(f"/api/potato/payouts/{payout_id}/pay", headers=op_hdr, json={"reason": "이체완료"})
        assert r.status_code == 204, r.text

        unreported = (await c.get("/api/potato/payouts/woncheon/unreported", headers=op_hdr)).json()
        row = next(x for x in unreported if x["payoutId"] == payout_id)
        assert row["hasSubject"] is False  # 주민번호 미등록 상태로 명확히 표시


async def test_withholding_subject_rejects_malformed_resident_number(app_db):
    async with _client() as c:
        token, acc = await login_account(c, "google", "x")
        hdr = {"Authorization": f"Bearer {token}"}
        await _seed_sale(app_db, acc["id"])
        await c.put("/api/me/bank-account", headers=hdr,
                    json={"holderName": "작가", "bank": "004", "accountNo": "1234567890"})
        payout_id = (await c.post("/api/me/payouts", headers=hdr)).json()["id"]
        op_hdr = {"Authorization": f"Bearer {await _op_token(c, app_db)}"}

        r = await c.put(
            f"/api/potato/payouts/{payout_id}/withholding-subject", headers=op_hdr,
            json={"residentNumber": "123"},
        )
        assert r.status_code == 422


async def test_withholding_subject_requires_operator_auth(app_db):
    async with _client() as c:
        r = await c.put(
            "/api/potato/payouts/00000000-0000-0000-0000-000000000000/withholding-subject",
            json={"residentNumber": RESIDENT_NO},
        )
        assert r.status_code == 401
        assert (await c.get("/api/potato/payouts/woncheon/unreported")).status_code == 401
