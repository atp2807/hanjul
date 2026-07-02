"""서평단 캠페인 E2E — 생성→모집→신청→배정(증정본)→서평단 리뷰."""
import httpx
import pytest
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import settings

settings.DEBUG = False

from main import app  # noqa: E402
from src.config.database import get_session  # noqa: E402
from src.features.auth.application.auth_service import AuthService  # noqa: E402
from src.features.auth.domain.models import SocialProfile  # noqa: E402
from src.features.auth.infrastructure.account_repo import SqlAccountRepository  # noqa: E402
from src.features.auth.presentation.dependencies import get_auth_service, token_issuer  # noqa: E402
from src.features.billing.application.order_service import OrderService  # noqa: E402
from src.features.billing.infrastructure.book_pricing import SqlBookPricing  # noqa: E402
from src.features.billing.infrastructure.order_repo import SqlOrderRepository  # noqa: E402
from src.features.billing.presentation.dependencies import get_order_service  # noqa: E402
from tests.fixtures.fake_account_repo import FakeProvider  # noqa: E402
from tests.fixtures.fake_order_repo import FakeGateway  # noqa: E402
from tests.integration.auth_helpers import login_account  # noqa: E402

AUTHOR = SocialProfile("GOOGLE", "cp-author", "a@x.com", "작가")
READER = SocialProfile("NAVER", "cp-reader", "r@x.com", "리뷰어")
OTHER = SocialProfile("KAKAO", "cp-other", "o@x.com", "남")


@pytest.fixture
def app_db(sessionmaker):
    async def _session():
        async with sessionmaker() as s:
            yield s

    def _auth(session: AsyncSession = Depends(get_session)):
        return AuthService(
            SqlAccountRepository(session),
            {"GOOGLE": FakeProvider("GOOGLE", AUTHOR), "NAVER": FakeProvider("NAVER", READER), "KAKAO": FakeProvider("KAKAO", OTHER)},
            token_issuer(),
        )

    def _order(session: AsyncSession = Depends(get_session)):
        return OrderService(SqlOrderRepository(session), FakeGateway(ok=True), SqlBookPricing(session))

    app.dependency_overrides[get_session] = _session
    app.dependency_overrides[get_auth_service] = _auth
    app.dependency_overrides[get_order_service] = _order
    yield
    app.dependency_overrides.clear()


async def test_campaign_full_flow(app_db):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        author_token, _ = await login_account(c, "google", "a")
        reader_token, reader = await login_account(c, "naver", "r")
        a_auth = {"Authorization": f"Bearer {author_token}"}
        r_auth = {"Authorization": f"Bearer {reader_token}"}

        book = (await c.post("/api/books", json={"title": "서평캠페인책"}, headers=a_auth)).json()["bookId"]
        await c.put(f"/api/books/{book}/price", json={"amount": 9000}, headers=a_auth)
        await c.post(f"/api/books/{book}/publish-now", headers=a_auth)

        # 작가만 캠페인 생성 — 타인 403
        assert (await c.post("/api/campaigns", json={"bookId": book, "slots": 1, "withdrawalConsent": True}, headers=r_auth)).status_code == 403
        cid = (await c.post("/api/campaigns", json={"bookId": book, "slots": 1, "withdrawalConsent": True}, headers=a_auth)).json()["campaignId"]

        # 모집 목록에 노출 + remaining 1
        open_list = (await c.get("/api/campaigns/open")).json()["items"]
        camp = next(x for x in open_list if x["id"] == cid)
        assert camp["remaining"] == 1
        # 상세 조회(공개)
        detail = (await c.get(f"/api/campaigns/{cid}")).json()
        assert detail["bookTitle"] == "서평캠페인책" and detail["remaining"] == 1

        # 리뷰어 신청
        assert (await c.post(f"/api/campaigns/{cid}/apply", headers=r_auth)).status_code == 204
        # 내 신청함 — PENDING
        apps = (await c.get("/api/me/applications", headers=r_auth)).json()["items"]
        assert apps[0]["status"] == "PENDING"
        # 신청자 목록 — 작가만(타인 403)
        assert (await c.get(f"/api/campaigns/{cid}/applications", headers=r_auth)).status_code == 403
        applicants = (await c.get(f"/api/campaigns/{cid}/applications", headers=a_auth)).json()["items"]
        assert len(applicants) == 1 and applicants[0]["applicantName"] == "리뷰어"

        # 배정 전엔 리뷰 불가(미구매)
        assert (await c.post(f"/api/books/{book}/reviews", json={"rating": 5}, headers=r_auth)).status_code == 403

        # 작가가 배정 → 증정본 지급
        assert (await c.post(f"/api/campaigns/{cid}/assign", json={"applicantId": reader["id"]}, headers=a_auth)).status_code == 204
        # 신청 ASSIGNED + 마감 설정
        apps = (await c.get("/api/me/applications", headers=r_auth)).json()["items"]
        assert apps[0]["status"] == "ASSIGNED" and apps[0]["deadlineAt"] is not None
        # 슬롯 다 차서 모집 마감
        assert (await c.get("/api/campaigns/open")).json()["items"] == [] or all(x["id"] != cid for x in (await c.get("/api/campaigns/open")).json()["items"])

        # 증정본으로 리뷰 → 서평단(REVIEW_COPY)
        assert (await c.post(f"/api/books/{book}/reviews", json={"rating": 5, "body": "사전 리뷰"}, headers=r_auth)).status_code == 201
        item = (await c.get(f"/api/books/{book}/reviews")).json()["items"][0]
        assert item["sourceCd"] == "REVIEW_COPY"
        # 리뷰 작성 → 신청 COMPLETED + 내 캠페인 집계
        apps = (await c.get("/api/me/applications", headers=r_auth)).json()["items"]
        assert apps[0]["status"] == "COMPLETED"
        mine = (await c.get("/api/me/campaigns", headers=a_auth)).json()["items"]
        row = next(x for x in mine if x["id"] == cid)
        assert row["applicants"] == 1 and row["reviewed"] == 1 and row["filled"] == 1
        # 리뷰어 신뢰도·자격 집계(엔드포인트)
        st = (await c.get("/api/me/reviewer-status", headers=r_auth)).json()
        assert st["completed"] == 1 and st["missed"] == 0 and st["completionRate"] == 100
        assert st["received"] == 1 and st["blockedUntil"] is None


async def test_open_campaigns_filter_by_category(app_db):
    """모집 목록 — 각 항목에 (책)장르 노출 + ?category= 로 필터."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        a_auth = {"Authorization": f"Bearer {(await login_account(c, 'google', 'a'))[0]}"}

        async def make(title, category):
            bid = (await c.post("/api/books", json={"title": title}, headers=a_auth)).json()["bookId"]
            await c.put(f"/api/books/{bid}/meta", json={"category": category}, headers=a_auth)
            await c.put(f"/api/books/{bid}/price", json={"amount": 1000}, headers=a_auth)
            await c.post(f"/api/books/{bid}/publish-now", headers=a_auth)
            await c.post("/api/campaigns", json={"bookId": bid, "slots": 2, "withdrawalConsent": True}, headers=a_auth)

        await make("소설책", "소설")
        await make("에세이책", "에세이")

        # 전체 — 장르 노출
        allc = (await c.get("/api/campaigns/open")).json()["items"]
        by_title = {x["bookTitle"]: x for x in allc}
        assert by_title["소설책"]["category"] == "소설" and by_title["에세이책"]["category"] == "에세이"

        # 장르 필터
        only = (await c.get("/api/campaigns/open?category=소설")).json()["items"]
        assert [x["bookTitle"] for x in only] == ["소설책"]


async def test_author_can_close_campaign(app_db):
    """작가가 모집을 수동 마감 — 피드에서 빠지고 새 신청 막힘. 기존 신청자는 여전히 배정 가능."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        a_auth = {"Authorization": f"Bearer {(await login_account(c, 'google', 'a'))[0]}"}
        reader_token, reader = await login_account(c, "naver", "r")
        r_auth = {"Authorization": f"Bearer {reader_token}"}
        other_token, _ = await login_account(c, "kakao", "o")
        o_auth = {"Authorization": f"Bearer {other_token}"}

        book = (await c.post("/api/books", json={"title": "마감책"}, headers=a_auth)).json()["bookId"]
        await c.put(f"/api/books/{book}/price", json={"amount": 1000}, headers=a_auth)
        await c.post(f"/api/books/{book}/publish-now", headers=a_auth)
        cid = (await c.post("/api/campaigns", json={"bookId": book, "slots": 2, "withdrawalConsent": True}, headers=a_auth)).json()["campaignId"]
        await c.post(f"/api/campaigns/{cid}/apply", headers=r_auth)  # 미리 신청

        # 작가 아닌 사람은 마감 불가
        assert (await c.post(f"/api/campaigns/{cid}/close", headers=r_auth)).status_code == 403
        # 작가 마감
        assert (await c.post(f"/api/campaigns/{cid}/close", headers=a_auth)).status_code == 204

        # 모집 피드에서 빠짐
        assert all(x["id"] != cid for x in (await c.get("/api/campaigns/open")).json()["items"])
        # 새 신청 차단(마감)
        assert (await c.post(f"/api/campaigns/{cid}/apply", headers=o_auth)).status_code == 409
        # 기존 신청자는 여전히 배정 가능(슬롯 남음)
        assert (await c.post(f"/api/campaigns/{cid}/assign", json={"applicantId": reader["id"]}, headers=a_auth)).status_code == 204


async def test_cancel_application(app_db):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        author_token, _ = await login_account(c, "google", "a")
        reader_token, reader = await login_account(c, "naver", "r")
        a_auth = {"Authorization": f"Bearer {author_token}"}
        r_auth = {"Authorization": f"Bearer {reader_token}"}

        book = (await c.post("/api/books", json={"title": "취소책"}, headers=a_auth)).json()["bookId"]
        await c.put(f"/api/books/{book}/price", json={"amount": 1000}, headers=a_auth)
        await c.post(f"/api/books/{book}/publish-now", headers=a_auth)
        cid = (await c.post("/api/campaigns", json={"bookId": book, "slots": 1, "withdrawalConsent": True}, headers=a_auth)).json()["campaignId"]

        await c.post(f"/api/campaigns/{cid}/apply", headers=r_auth)
        assert len((await c.get("/api/me/applications", headers=r_auth)).json()["items"]) == 1
        # 신청 취소(PENDING)
        assert (await c.delete(f"/api/campaigns/{cid}/apply", headers=r_auth)).status_code == 204
        assert (await c.get("/api/me/applications", headers=r_auth)).json()["items"] == []
        # 취소 후 배정 시도 → 신청자 아님(409)
        assert (await c.post(f"/api/campaigns/{cid}/assign", json={"applicantId": reader["id"]}, headers=a_auth)).status_code == 409


async def test_assign_notifies_reviewer(app_db):
    """배정되면 리뷰어 알림함에 '배정' 알림이 떠야 한다 (증정본 도착 안내)."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        author_token, _ = await login_account(c, "google", "a")
        reader_token, reader = await login_account(c, "naver", "r")
        a_auth = {"Authorization": f"Bearer {author_token}"}
        r_auth = {"Authorization": f"Bearer {reader_token}"}

        book = (await c.post("/api/books", json={"title": "알림책"}, headers=a_auth)).json()["bookId"]
        await c.put(f"/api/books/{book}/price", json={"amount": 1000}, headers=a_auth)
        await c.post(f"/api/books/{book}/publish-now", headers=a_auth)
        cid = (await c.post("/api/campaigns", json={"bookId": book, "slots": 1, "withdrawalConsent": True}, headers=a_auth)).json()["campaignId"]
        await c.post(f"/api/campaigns/{cid}/apply", headers=r_auth)

        # 배정 전: 알림 없음
        before = (await c.get("/api/me/notifications", headers=r_auth)).json()
        assert before["unreadCount"] == 0

        # 배정
        assert (await c.post(f"/api/campaigns/{cid}/assign", json={"applicantId": reader["id"]}, headers=a_auth)).status_code == 204

        # 배정 후: 리뷰어에게 ASSIGNED 알림(책 제목 포함, 안읽음)
        after = (await c.get("/api/me/notifications", headers=r_auth)).json()
        assert after["unreadCount"] >= 1
        item = next(n for n in after["items"] if n["kindCd"] == "ASSIGNED")
        assert item["title"] == "알림책" and item["bookId"] == book and item["readYn"] is False


async def test_assign_only_by_campaign_author(app_db):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        author_token, _ = await login_account(c, "google", "a")
        reader_token, reader = await login_account(c, "naver", "r")
        other_token, _ = await login_account(c, "kakao", "o")
        a_auth = {"Authorization": f"Bearer {author_token}"}
        r_auth = {"Authorization": f"Bearer {reader_token}"}
        o_auth = {"Authorization": f"Bearer {other_token}"}

        book = (await c.post("/api/books", json={"title": "캠책2"}, headers=a_auth)).json()["bookId"]
        await c.put(f"/api/books/{book}/price", json={"amount": 1000}, headers=a_auth)
        await c.post(f"/api/books/{book}/publish-now", headers=a_auth)
        cid = (await c.post("/api/campaigns", json={"bookId": book, "slots": 1, "withdrawalConsent": True}, headers=a_auth)).json()["campaignId"]
        await c.post(f"/api/campaigns/{cid}/apply", headers=r_auth)

        # 남이 배정 시도 → 403
        assert (await c.post(f"/api/campaigns/{cid}/assign", json={"applicantId": reader["id"]}, headers=o_auth)).status_code == 403
