"""연령 게이트(dc-daeb0d3d) E2E — 스토어 필터링·구매/열람 차단·신분증 인증(potato 승인/거부)."""
import httpx
import pytest
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.config.settings import settings

settings.DEBUG = False

from main import app  # noqa: E402
from src.config.database import get_potato_session, get_session  # noqa: E402
from src.features.auth.application.auth_service import AuthService  # noqa: E402
from src.features.auth.domain.models import SocialProfile  # noqa: E402
from src.features.auth.infrastructure.account_repo import SqlAccountRepository  # noqa: E402
from src.features.auth.presentation.dependencies import get_auth_service, token_issuer  # noqa: E402
from src.features.potato.application.password import hash_password  # noqa: E402
from src.features.potato.domain.models import OPERATOR  # noqa: E402
from src.features.potato.infrastructure.operator_repo import SqlOperatorRepository  # noqa: E402

from tests.fixtures.fake_account_repo import FakeProvider  # noqa: E402
from tests.integration.auth_helpers import login_account  # noqa: E402
from tests.integration.book_helpers import create_book, import_raw, publish_priced_book  # noqa: E402

AUTHOR = SocialProfile("GOOGLE", "age-gate-author", "agegate@x.com", "작가")
# 별도 provider(NAVER)로 두 번째 독립 신원 — 작가 본인은 연령 게이트를 우회하므로
# "미인증 구매자/독자" 시나리오는 반드시 작가와 다른 계정으로 로그인해야 한다.
READER = SocialProfile("NAVER", "age-gate-reader", "agegatereader@x.com", "독자")
OP_EMAIL, OP_PW = "agegateop@hanjul.io", "potato-agegate-123"


@pytest.fixture
def app_db(sessionmaker):
    async def _session():
        async with sessionmaker() as s:
            yield s

    def _auth(session: AsyncSession = Depends(get_session)):
        return AuthService(
            SqlAccountRepository(session),
            {"GOOGLE": FakeProvider("GOOGLE", AUTHOR), "NAVER": FakeProvider("NAVER", READER)},
            token_issuer(),
        )

    app.dependency_overrides[get_session] = _session
    app.dependency_overrides[get_potato_session] = _session
    app.dependency_overrides[get_auth_service] = _auth
    yield sessionmaker
    app.dependency_overrides.clear()


def _client():
    # loopback client IP — potato IP 화이트리스트가 설정된 상태로 실행돼도 안전(payouts e2e와 동일 관례)
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app, client=("127.0.0.1", 50000)), base_url="http://t"
    )


async def _op_token(c) -> str:
    r = await c.post("/api/potato/auth/login", json={"email": OP_EMAIL, "password": OP_PW})
    return r.json()["token"]


async def _rate_age18(c, book_id: str, headers: dict) -> None:
    """작가 오버라이드로 책 등급을 AGE18로 설정 (분류기 미필요 — set_rating은 순수 병합)."""
    r = await c.put(
        f"/api/books/{book_id}/content-rating",
        json={"detail": {"sexual": "AGE18"}},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    assert r.json()["contentRating"] == "AGE18"


@pytest.fixture
async def op_ready(app_db):
    """potato 운영자 계정 시딩 — app_db가 get_potato_session도 오버라이드해뒀으므로 같은 세션 재사용."""
    async with app_db() as s:
        await SqlOperatorRepository(s).create(
            email=OP_EMAIL, name="운영자", role=OPERATOR, password_hash=hash_password(OP_PW)
        )


async def test_store_listing_hides_restricted_book(app_db, op_ready):
    async with _client() as c:
        token, _ = await login_account(c, "google", "x")
        hdr = {"Authorization": f"Bearer {token}"}

        all_book = await publish_priced_book(c, hdr, title="일반책", price=1000)
        age18_book = await publish_priced_book(c, hdr, title="성인책", price=1000)
        await _rate_age18(c, age18_book, hdr)

        # 비로그인 — AGE18 책 안 보임
        anon_items = (await c.get("/api/store/books")).json()["items"]
        anon_ids = {b["id"] for b in anon_items}
        assert all_book in anon_ids
        assert age18_book not in anon_ids

        # 로그인했지만 미인증 — 여전히 안 보임
        my_items = (await c.get("/api/store/books", headers=hdr)).json()["items"]
        my_ids = {b["id"] for b in my_items}
        assert all_book in my_ids
        assert age18_book not in my_ids

        # 인증(AGE18) 후 — 목록에 나타남
        op_hdr = {"Authorization": f"Bearer {await _op_token(c)}"}
        upload = await c.post(
            "/api/me/age-verification",
            headers=hdr,
            files={"file": ("id.jpg", b"fake-id-photo-bytes", "image/jpeg")},
        )
        assert upload.status_code == 201, upload.text
        request_id = upload.json()["id"]
        assert (
            await c.post(f"/api/potato/age-verification/{request_id}/approve", headers=op_hdr)
        ).status_code == 204

        verified_items = (await c.get("/api/store/books", headers=hdr)).json()["items"]
        assert age18_book in {b["id"] for b in verified_items}


async def test_order_and_content_blocked_then_allowed_after_verification(app_db, op_ready):
    async with _client() as c:
        # 작가(google) — 책을 발행하고 AGE18로 등급 설정. 작가 본인은 게이트 우회 대상이라
        # "미인증이면 막힘"을 검증하려면 반드시 다른 계정(독자, naver)으로 시도해야 한다.
        author_token, _ = await login_account(c, "google", "x")
        author_hdr = {"Authorization": f"Bearer {author_token}"}
        book_id = await publish_priced_book(c, author_hdr, title="성인책2", price=2000)
        await _rate_age18(c, book_id, author_hdr)

        reader_token, _ = await login_account(c, "naver", "y")
        hdr = {"Authorization": f"Bearer {reader_token}"}

        # 구매 시도 — 미인증 403 (AgeVerificationRequired)
        order = await c.post(
            "/api/orders", headers=hdr,
            json={"bookId": book_id, "channel": "SELF", "withdrawalConsent": True},
        )
        assert order.status_code == 403, order.text

        # 본문열람 시도 — 미인증 403
        content = await c.get(f"/api/books/{book_id}/content", headers=hdr)
        assert content.status_code == 403, content.text

        # 성인인증 진행 (신분증 업로드 → potato 승인)
        upload = await c.post(
            "/api/me/age-verification", headers=hdr,
            files={"file": ("id.png", b"fake-id-photo-png", "image/png")},
        )
        assert upload.status_code == 201, upload.text
        request_id = upload.json()["id"]

        op_hdr = {"Authorization": f"Bearer {await _op_token(c)}"}
        assert (
            await c.post(f"/api/potato/age-verification/{request_id}/approve", headers=op_hdr)
        ).status_code == 204

        # /api/me 에 verifiedTier 반영
        me = (await c.get("/api/me", headers=hdr)).json()
        assert me["verifiedTier"] == "AGE18"

        # 이제 구매·열람 모두 통과
        order2 = await c.post(
            "/api/orders", headers=hdr,
            json={"bookId": book_id, "channel": "SELF", "withdrawalConsent": True},
        )
        assert order2.status_code == 201, order2.text

        content2 = await c.get(f"/api/books/{book_id}/content", headers=hdr)
        assert content2.status_code == 200, content2.text


async def test_book_owner_reads_own_restricted_content_without_verification(app_db):
    """소유 작가는 본인이 AGE18로 등급 매긴 원고를 미인증 상태로도 (프리뷰가 아니라) 열람 가능.

    가격 미설정(무료 취급) 책으로 검증 — 유료 미구매 시의 프리뷰 축약 응답은
    content_rating을 보존하지 않는 기존(이 작업과 무관한) 동작이라 여기서는 피한다.
    """
    async with _client() as c:
        token, _ = await login_account(c, "google", "x")
        hdr = {"Authorization": f"Bearer {token}"}
        book_id = await create_book(c, hdr, title="내 성인 원고")
        await import_raw(c, book_id, "본문 내용", hdr)
        await _rate_age18(c, book_id, hdr)

        r = await c.get(f"/api/books/{book_id}/content", headers=hdr)
        assert r.status_code == 200, r.text
        assert r.json()["isPreview"] is False
        assert r.json()["contentRating"] == "AGE18"


async def test_submit_duplicate_pending_is_conflict(app_db):
    async with _client() as c:
        token, _ = await login_account(c, "google", "x")
        hdr = {"Authorization": f"Bearer {token}"}

        # 제출 전 — 진행중 요청 없음 → null
        before = await c.get("/api/me/age-verification", headers=hdr)
        assert before.status_code == 200
        assert before.json() is None

        first = await c.post(
            "/api/me/age-verification", headers=hdr,
            files={"file": ("a.jpg", b"one", "image/jpeg")},
        )
        assert first.status_code == 201, first.text

        second = await c.post(
            "/api/me/age-verification", headers=hdr,
            files={"file": ("b.jpg", b"two", "image/jpeg")},
        )
        assert second.status_code == 409, second.text

        status = (await c.get("/api/me/age-verification", headers=hdr)).json()
        assert status["status"] == "PENDING"


async def test_reject_deletes_photo_without_tier_change(app_db, op_ready):
    async with _client() as c:
        token, _ = await login_account(c, "google", "x")
        hdr = {"Authorization": f"Bearer {token}"}
        upload = await c.post(
            "/api/me/age-verification", headers=hdr,
            files={"file": ("id.webp", b"fake-webp-bytes", "image/webp")},
        )
        request_id = upload.json()["id"]

        op_hdr = {"Authorization": f"Bearer {await _op_token(c)}"}
        # 승인 전 — 사진 열람 가능
        photo = await c.get(f"/api/potato/age-verification/{request_id}/photo", headers=op_hdr)
        assert photo.status_code == 200
        assert photo.content == b"fake-webp-bytes"
        assert photo.headers["content-type"] == "image/webp"

        reject = await c.post(
            f"/api/potato/age-verification/{request_id}/reject", headers=op_hdr,
            json={"reason": "사진 식별 불가"},
        )
        assert reject.status_code == 204, reject.text

        # 거부는 등급 변경 없음
        me = (await c.get("/api/me", headers=hdr)).json()
        assert me["verifiedTier"] == "ALL"

        # 심사완료 즉시 원본 삭제 — 사진 재조회 404
        photo_after = await c.get(f"/api/potato/age-verification/{request_id}/photo", headers=op_hdr)
        assert photo_after.status_code == 404

        # 새 요청 재제출 가능(이전 요청이 더 이상 PENDING 아님)
        resubmit = await c.post(
            "/api/me/age-verification", headers=hdr,
            files={"file": ("id2.jpg", b"retry", "image/jpeg")},
        )
        assert resubmit.status_code == 201, resubmit.text


async def test_potato_age_verification_requires_operator_not_customer_token(app_db):
    async with _client() as c:
        token, _ = await login_account(c, "google", "x")
        # 고객 토큰으로 운영자 심사큐 접근 → 401(방화벽, 다른 시크릿)
        r = await c.get(
            "/api/potato/age-verification", headers={"Authorization": f"Bearer {token}"}
        )
        assert r.status_code == 401

        r2 = await c.get("/api/potato/age-verification")
        assert r2.status_code == 401


async def test_upload_rejects_non_image_file(app_db):
    async with _client() as c:
        token, _ = await login_account(c, "google", "x")
        hdr = {"Authorization": f"Bearer {token}"}
        r = await c.post(
            "/api/me/age-verification", headers=hdr,
            files={"file": ("id.txt", b"not-an-image", "text/plain")},
        )
        assert r.status_code == 422
