"""신고 큐 E2E — 고객 접수 → 운영자 목록 → 처리 + 감사."""
from uuid import uuid4

import httpx
from main import app
from sqlalchemy import select
from src.features.auth.presentation.dependencies import token_issuer as customer_token
from src.features.potato.application.password import hash_password
from src.features.potato.domain.models import OPERATOR
from src.features.potato.infrastructure.operator_repo import SqlOperatorRepository
from src.infrastructure.db.models.operator import AuditLog
from src.infrastructure.db.models.report import Report

EMAIL = "report-op@hanjul.io"
PASSWORD = "potato-rep-123"


async def _op_token(c, sessionmaker) -> str:
    async with sessionmaker() as s:
        await SqlOperatorRepository(s).create(
            email=EMAIL, name="운영자", role=OPERATOR, password_hash=hash_password(PASSWORD)
        )
    r = await c.post("/api/potato/auth/login", json={"email": EMAIL, "password": PASSWORD})
    return r.json()["token"]


def _client():
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app, client=("127.0.0.1", 50000)), base_url="http://t"
    )


async def test_report_submit_list_resolve(app_db_potato):
    async with _client() as c:
        op_hdr = {"Authorization": f"Bearer {await _op_token(c, app_db_potato)}"}
        # 고객이 책 신고
        cust_hdr = {"Authorization": f"Bearer {customer_token().issue(uuid4(), 'READER')}"}
        target = str(uuid4())
        sub = await c.post(
            "/api/reports",
            headers=cust_hdr,
            json={"targetType": "BOOK", "targetId": target, "reason": "혐오 표현"},
        )
        assert sub.status_code == 201, sub.text
        report_id = sub.json()["id"]

        # 잘못된 대상 타입 → 422
        bad = await c.post(
            "/api/reports",
            headers=cust_hdr,
            json={"targetType": "PLANET", "targetId": target, "reason": "x"},
        )
        assert bad.status_code == 422

        # 무인증 신고 → 401
        assert (
            await c.post("/api/reports", json={"targetType": "BOOK", "targetId": target, "reason": "x"})
        ).status_code == 401

        # 운영자 큐에 보임
        queue = (await c.get("/api/potato/reports", headers=op_hdr)).json()
        assert any(r["id"] == report_id for r in queue)
        assert queue[0]["targetType"] == "BOOK"

        # 운영자 처리(RESOLVE)
        r = await c.post(
            f"/api/potato/reports/{report_id}/resolve",
            headers=op_hdr,
            json={"action": "RESOLVE", "resolution": "해당 책 takedown 완료"},
        )
        assert r.status_code == 204, r.text

        # OPEN 큐에서 빠짐
        open_queue = (await c.get("/api/potato/reports", headers=op_hdr)).json()
        assert all(rr["id"] != report_id for rr in open_queue)

        # DB 상태 + 감사
        async with app_db_potato() as s:
            rep = (await s.execute(select(Report))).scalar_one()
            assert rep.status == "RESOLVED"
            assert rep.resolved_by is not None
            audits = (await s.execute(select(AuditLog))).scalars().all()
        assert any(a.action == "RESOLVE_REPORT" for a in audits)


async def test_reports_queue_requires_operator(app_db_potato):
    async with _client() as c:
        # 고객 토큰으로 운영자 큐 접근 → 401 (방화벽)
        cust_hdr = {"Authorization": f"Bearer {customer_token().issue(uuid4(), 'READER')}"}
        assert (await c.get("/api/potato/reports", headers=cust_hdr)).status_code == 401
