"""운영자 계정 조치(정지·서평단차단) + 대시보드 E2E."""
from datetime import datetime, timezone
from uuid import uuid4

import httpx
import pytest

from src.config.settings import settings

settings.DEBUG = False

from main import app  # noqa: E402
from src.config.database import get_potato_session, get_session  # noqa: E402
from src.features.potato.application.password import hash_password  # noqa: E402
from src.features.potato.domain.models import OPERATOR  # noqa: E402
from src.features.potato.infrastructure.operator_repo import SqlOperatorRepository  # noqa: E402
from src.infrastructure.db.models.account import Account  # noqa: E402
from src.infrastructure.db.models.book import Book  # noqa: E402

EMAIL = "acct-op@hanjul.io"
PASSWORD = "potato-acct-123"


@pytest.fixture
def app_db(sessionmaker):
    async def _session():
        async with sessionmaker() as s:
            yield s

    app.dependency_overrides[get_session] = _session
    app.dependency_overrides[get_potato_session] = _session
    yield sessionmaker
    app.dependency_overrides.clear()


async def _op_token(c, sessionmaker) -> str:
    async with sessionmaker() as s:
        await SqlOperatorRepository(s).create(
            email=EMAIL, name="운영자", role=OPERATOR, password_hash=hash_password(PASSWORD)
        )
    r = await c.post("/api/potato/auth/login", json={"email": EMAIL, "password": PASSWORD})
    return r.json()["token"]


async def _make_account(sessionmaker) -> str:
    aid = uuid4()
    async with sessionmaker() as s:
        s.add(Account(id=aid, email="reader@x.com", display_name="독자", role="READER"))
        await s.commit()
    return str(aid)


def _client():
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app, client=("127.0.0.1", 50000)), base_url="http://t"
    )


async def test_suspend_and_block_review_with_audit(app_db):
    async with _client() as c:
        hdr = {"Authorization": f"Bearer {await _op_token(c, app_db)}"}
        aid = await _make_account(app_db)

        # 초기 상태
        view = (await c.get(f"/api/potato/accounts/{aid}", headers=hdr)).json()
        assert view["status"] == "ACTIVE"
        assert view["reviewBlocked"] is False

        # 정지
        assert (
            await c.post(f"/api/potato/accounts/{aid}/suspend", headers=hdr, json={"reason": "어뷰징"})
        ).status_code == 204
        # 서평단 자격회수
        assert (
            await c.post(f"/api/potato/accounts/{aid}/block-review", headers=hdr, json={})
        ).status_code == 204

        view = (await c.get(f"/api/potato/accounts/{aid}", headers=hdr)).json()
        assert view["status"] == "SUSPENDED"
        assert view["reviewBlocked"] is True

        # 해제
        assert (await c.post(f"/api/potato/accounts/{aid}/unsuspend", headers=hdr)).status_code == 204
        assert (
            await c.post(f"/api/potato/accounts/{aid}/unblock-review", headers=hdr)
        ).status_code == 204
        view = (await c.get(f"/api/potato/accounts/{aid}", headers=hdr)).json()
        assert view["status"] == "ACTIVE"
        assert view["reviewBlocked"] is False

        # 없는 계정 → 404
        assert (
            await c.post(f"/api/potato/accounts/{uuid4()}/suspend", headers=hdr, json={})
        ).status_code == 404


async def test_dashboard_stats(app_db):
    async with _client() as c:
        hdr = {"Authorization": f"Bearer {await _op_token(c, app_db)}"}
        await _make_account(app_db)
        # 출판 책 1 + 차단 책 1
        async with app_db() as s:
            s.add(Book(id=uuid4(), title="공개", kind="BOOK", language="ko", status="PUBLISHED",
                       price_amt=1000, published_at=datetime.now(timezone.utc)))
            s.add(Book(id=uuid4(), title="차단", kind="BOOK", language="ko", status="PUBLISHED",
                       price_amt=1000, published_at=datetime.now(timezone.utc),
                       blocked_at=datetime.now(timezone.utc)))
            await s.commit()

        stats = (await c.get("/api/potato/dashboard/stats", headers=hdr)).json()
        assert stats["accounts"] == 1
        assert stats["booksTotal"] == 2
        assert stats["booksPublished"] == 1
        assert stats["booksBlocked"] == 1
        assert stats["reportsOpen"] == 0

        # 방화벽 — 무인증 401
        assert (await c.get("/api/potato/dashboard/stats")).status_code == 401
