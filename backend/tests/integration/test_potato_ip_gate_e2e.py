"""운영자 영역 IP 화이트리스트 게이트.

운영(api.hanjul.io는 Cloudflare 프록시)에선 CF-Connecting-IP 가 진짜 클라 IP.
"""
import httpx
import pytest

from src.config.settings import settings

settings.DEBUG = False

from main import app  # noqa: E402
from src.config.database import get_potato_session, get_session  # noqa: E402


@pytest.fixture
def app_db(sessionmaker):
    async def _session():
        async with sessionmaker() as s:
            yield s

    app.dependency_overrides[get_session] = _session
    app.dependency_overrides[get_potato_session] = _session
    yield sessionmaker
    app.dependency_overrides.clear()


def _client(client_host="203.0.113.9"):
    # 비-loopback 클라이언트 → 게이트 자체를 검증 (loopback 우회 안 탐)
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app, client=(client_host, 12345)), base_url="http://t"
    )


async def test_whitelist_blocks_non_listed_ip(app_db, monkeypatch):
    monkeypatch.setattr(settings, "POTATO_ALLOWED_IPS", "198.51.100.7")
    async with _client() as c:
        # CF 헤더 없음 + 비-loopback → 403 (로그인조차 차단)
        r = await c.post("/api/potato/auth/login", json={"email": "x@x.io", "password": "y"})
        assert r.status_code == 403, r.text
        # 화이트리스트 IP → 게이트 통과 (자격증명 틀려 401)
        r2 = await c.post(
            "/api/potato/auth/login",
            json={"email": "x@x.io", "password": "y"},
            headers={"CF-Connecting-IP": "198.51.100.7"},
        )
        assert r2.status_code == 401
        # 다른 IP → 403
        r3 = await c.get(
            "/api/potato/dashboard/stats", headers={"CF-Connecting-IP": "8.8.8.8"}
        )
        assert r3.status_code == 403


async def test_empty_whitelist_allows_all(app_db, monkeypatch):
    monkeypatch.setattr(settings, "POTATO_ALLOWED_IPS", "")
    async with _client() as c:
        # 리스트 비면 비-loopback도 통과 (게이트 무시) → 자격증명 401
        r = await c.post("/api/potato/auth/login", json={"email": "x@x.io", "password": "y"})
        assert r.status_code == 401


async def test_customer_reports_endpoint_not_gated(app_db, monkeypatch):
    """고객 신고 접수(/api/reports)는 게이트 없음 — 인증만 요구(401)."""
    monkeypatch.setattr(settings, "POTATO_ALLOWED_IPS", "198.51.100.7")
    async with _client() as c:
        r = await c.post("/api/reports", json={"targetType": "BOOK", "targetId": "x", "reason": "y"})
        assert r.status_code == 401  # 403(IP) 아님 — 게이트 미적용
