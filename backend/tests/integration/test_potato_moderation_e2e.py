"""운영자 모더레이션 E2E — 책 takedown → 스토어에서 사라짐 → 복원 + 감사로그."""
from datetime import UTC, datetime
from uuid import uuid4

import httpx
from main import app
from sqlalchemy import select
from src.features.potato.application.password import hash_password
from src.features.potato.domain.models import OPERATOR
from src.features.potato.infrastructure.operator_repo import SqlOperatorRepository
from src.infrastructure.db.models.book import Book
from src.infrastructure.db.models.operator import AuditLog

EMAIL = "mod@hanjul.io"
PASSWORD = "potato-mod-123"


async def _login(c, sessionmaker) -> str:
    async with sessionmaker() as s:
        await SqlOperatorRepository(s).create(
            email=EMAIL, name="모더레이터", role=OPERATOR, password_hash=hash_password(PASSWORD)
        )
    r = await c.post("/api/potato/auth/login", json={"email": EMAIL, "password": PASSWORD})
    return r.json()["token"]


async def _make_published_book(sessionmaker, title="문제의 책") -> str:
    book_id = uuid4()
    async with sessionmaker() as s:
        s.add(
            Book(
                id=book_id,
                title=title,
                kind="BOOK",
                language="ko",
                status="PUBLISHED",
                price_amt=1000,
                published_at=datetime.now(UTC),
            )
        )
        await s.commit()
    return str(book_id)


def _client():
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app, client=("127.0.0.1", 50000)), base_url="http://t"
    )


async def test_takedown_hides_from_store_and_audits(app_db_potato):
    async with _client() as c:
        token = await _login(c, app_db_potato)
        hdr = {"Authorization": f"Bearer {token}"}
        book_id = await _make_published_book(app_db_potato)

        # 처음엔 스토어에 보임
        assert (await c.get(f"/api/store/books/{book_id}")).status_code == 200

        # 운영자 takedown
        r = await c.post(
            f"/api/potato/books/{book_id}/takedown", headers=hdr, json={"reason": "저작권 침해"}
        )
        assert r.status_code == 204, r.text

        # 스토어에서 사라짐 (404)
        assert (await c.get(f"/api/store/books/{book_id}")).status_code == 404
        # 스토어 목록에서도 제외
        listed = (await c.get("/api/store/books")).json()["items"]
        assert all(b["id"] != book_id for b in listed)

        # 운영자 목록엔 차단표시로 보임
        ops_books = (await c.get("/api/potato/books", headers=hdr)).json()
        target = next(b for b in ops_books if b["id"] == book_id)
        assert target["blocked"] is True

        # 감사로그 1건
        async with app_db_potato() as s:
            rows = (await s.execute(select(AuditLog))).scalars().all()
        assert len(rows) == 1
        assert rows[0].action == "TAKEDOWN"
        assert rows[0].entity_type == "BOOK"
        assert rows[0].detail == {"reason": "저작권 침해"}

        # 복원 → 다시 스토어에 보임
        assert (
            await c.post(f"/api/potato/books/{book_id}/restore", headers=hdr)
        ).status_code == 204
        assert (await c.get(f"/api/store/books/{book_id}")).status_code == 200


async def test_takedown_requires_operator_token(app_db_potato):
    async with _client() as c:
        book_id = await _make_published_book(app_db_potato)
        # 무인증 → 401
        assert (
            await c.post(f"/api/potato/books/{book_id}/takedown")
        ).status_code == 401
