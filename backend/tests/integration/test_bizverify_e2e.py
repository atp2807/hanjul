"""사업자등록번호 진위확인 E2E — 인증 게이트 + 검증 흐름(FakeBusinessRegistry 주입)."""
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
from src.features.bizverify.application.bizverify_service import BizVerifyService  # noqa: E402
from src.features.bizverify.domain.models import BusinessRegistration  # noqa: E402
from src.features.bizverify.infrastructure.nts_registry import NtsBusinessRegistry  # noqa: E402
from src.features.bizverify.presentation.dependencies import get_bizverify_service  # noqa: E402

from tests.fixtures.fake_account_repo import FakeProvider  # noqa: E402
from tests.fixtures.fake_business_registry import FakeBusinessRegistry  # noqa: E402
from tests.integration.auth_helpers import login_account  # noqa: E402

PROFILE = SocialProfile("GOOGLE", "biz-x", "biz@x.com", "작가")
VALID_NO = "2208162517"


@pytest.fixture
def app_db(sessionmaker):
    async def _session():
        async with sessionmaker() as s:
            yield s

    def _auth(session: AsyncSession = Depends(get_session)):
        return AuthService(
            SqlAccountRepository(session),
            {"GOOGLE": FakeProvider("GOOGLE", PROFILE)},
            token_issuer(),
        )

    app.dependency_overrides[get_session] = _session
    app.dependency_overrides[get_auth_service] = _auth
    yield
    app.dependency_overrides.clear()


def _override_registry(result):
    app.dependency_overrides[get_bizverify_service] = lambda: BizVerifyService(
        FakeBusinessRegistry(result=result)
    )


async def test_unauthenticated_returns_401(app_db):
    _override_registry(None)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/api/business-number/verify", params={"businessNo": VALID_NO})
        assert r.status_code == 401


async def test_invalid_format_returns_422(app_db):
    _override_registry(None)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        token, _ = await login_account(c, "google", "x")
        auth = {"Authorization": f"Bearer {token}"}
        r = await c.get("/api/business-number/verify", params={"businessNo": "1234567890"}, headers=auth)
        assert r.status_code == 422


async def test_valid_but_not_registered_returns_404(app_db):
    _override_registry(None)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        token, _ = await login_account(c, "google", "x")
        auth = {"Authorization": f"Bearer {token}"}
        r = await c.get("/api/business-number/verify", params={"businessNo": VALID_NO}, headers=auth)
        assert r.status_code == 404


async def test_valid_and_registered_returns_200(app_db):
    reg = BusinessRegistration(
        business_no=VALID_NO,
        name="포테이토크래프트",
        ceo_name="홍길동",
        status="01",
        status_name="계속사업자",
        is_active=True,
    )
    _override_registry(reg)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        token, _ = await login_account(c, "google", "x")
        auth = {"Authorization": f"Bearer {token}"}
        r = await c.get("/api/business-number/verify", params={"businessNo": "220-81-62517"}, headers=auth)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["businessNo"] == VALID_NO
        assert body["name"] == "포테이토크래프트"
        assert body["ceoName"] == "홍길동"
        assert body["status"] == "01"
        assert body["statusName"] == "계속사업자"
        assert body["isActive"] is True


async def test_api_key_unconfigured_returns_503_not_500(app_db):
    """NTS_BUSINESS_API_KEY 미설정(현재 운영 실상태) — RuntimeError 가 500 스택트레이스로 새지 않고 503."""
    app.dependency_overrides[get_bizverify_service] = lambda: BizVerifyService(
        NtsBusinessRegistry(api_key="")
    )
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        token, _ = await login_account(c, "google", "x")
        auth = {"Authorization": f"Bearer {token}"}
        r = await c.get("/api/business-number/verify", params={"businessNo": VALID_NO}, headers=auth)
        assert r.status_code == 503
