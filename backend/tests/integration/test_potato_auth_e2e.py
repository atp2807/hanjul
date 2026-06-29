"""운영자(potato) 인증 E2E + 고객↔운영자 방화벽.

핵심 불변식: 고객 JWT 는 potato 를 못 뚫고, potato JWT 는 고객 엔드포인트에서 무효.
"""
from uuid import uuid4

import httpx
import pytest
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import settings

settings.DEBUG = False

from main import app  # noqa: E402
from src.config.database import get_session  # noqa: E402
from src.features.auth.presentation.dependencies import token_issuer as customer_token_issuer  # noqa: E402
from src.features.potato.application.password import hash_password  # noqa: E402
from src.features.potato.domain.models import DEVELOPER  # noqa: E402
from src.features.potato.infrastructure.operator_repo import SqlOperatorRepository  # noqa: E402

EMAIL = "op@hanjul.io"
PASSWORD = "potato-secret-123"


@pytest.fixture
def app_db(sessionmaker):
    async def _session():
        async with sessionmaker() as s:
            yield s

    app.dependency_overrides[get_session] = _session
    yield sessionmaker
    app.dependency_overrides.clear()


async def _seed_operator(sessionmaker, role: str = DEVELOPER) -> None:
    async with sessionmaker() as s:
        await SqlOperatorRepository(s).create(
            email=EMAIL, name="운영자", role_cd=role, password_hash=hash_password(PASSWORD)
        )


def _client():
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app, client=("127.0.0.1", 50000)), base_url="http://t"
    )


async def test_login_success_and_me(app_db):
    await _seed_operator(app_db)
    async with _client() as c:
        # 틀린 비번 → 401
        bad = await c.post("/api/potato/auth/login", json={"email": EMAIL, "password": "wrong"})
        assert bad.status_code == 401, bad.text
        # 없는 이메일 → 401 (존재 여부 비노출)
        nope = await c.post("/api/potato/auth/login", json={"email": "x@x.io", "password": PASSWORD})
        assert nope.status_code == 401
        # 성공 → 토큰 + role
        ok = await c.post("/api/potato/auth/login", json={"email": EMAIL, "password": PASSWORD})
        assert ok.status_code == 200, ok.text
        body = ok.json()
        assert body["roleCd"] == "DEVELOPER"
        token = body["token"]
        # me
        me = await c.get("/api/potato/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me.status_code == 200
        assert me.json()["email"] == EMAIL
        assert me.json()["roleCd"] == "DEVELOPER"


async def test_me_requires_token(app_db):
    await _seed_operator(app_db)
    async with _client() as c:
        assert (await c.get("/api/potato/auth/me")).status_code == 401
        assert (
            await c.get("/api/potato/auth/me", headers={"Authorization": "Bearer garbage"})
        ).status_code == 401


async def test_firewall_both_directions(app_db):
    """고객 토큰은 potato 에서 무효 / potato 토큰은 고객 엔드포인트에서 무효."""
    await _seed_operator(app_db)
    async with _client() as c:
        # 고객 토큰(다른 시크릿, aud 없음) → potato me 거부
        customer_token = customer_token_issuer().issue(uuid4(), "READER")
        r1 = await c.get(
            "/api/potato/auth/me", headers={"Authorization": f"Bearer {customer_token}"}
        )
        assert r1.status_code == 401

        # potato 토큰 → 고객 엔드포인트(/api/me) 거부
        login = await c.post("/api/potato/auth/login", json={"email": EMAIL, "password": PASSWORD})
        potato_token = login.json()["token"]
        r2 = await c.get("/api/me", headers={"Authorization": f"Bearer {potato_token}"})
        assert r2.status_code == 401
