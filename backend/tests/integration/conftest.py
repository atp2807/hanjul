"""통합 테스트 공용 — 실 SQLAlchemy 엔진(in-memory SQLite)으로 ORM/레포를 검증.

운영은 PostgreSQL 이지만, 이식 가능한 스모크를 위해 SQLite 사용:
- schema_translate_map={'pub': None} → pub 스키마를 SQLite 에서 무시 (모델 변경 0)
- StaticPool + 단일 연결 → in-memory DB 를 모든 세션이 공유

아래 공용 앱/DB 픽스처(app_db 계열·client 계열)는 기존 34개 테스트 파일의 로컬 app_db
픽스처와 동일한 오버라이드 구성을 일반화한 것. 기존 파일은 각자 로컬 정의를 그대로 쓰므로
(pytest는 테스트 모듈에 정의된 동일 이름 픽스처를 conftest 것보다 우선한다) 영향 없음 —
신규 테스트가 매번 보일러플레이트를 다시 쓰지 않도록 하는 용도.
"""
import httpx
import pytest
import pytest_asyncio
import src.infrastructure.db.models  # noqa: F401  (메타데이터 등록)
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool
from src.config.database import Base
from src.config.settings import settings

settings.DEBUG = False  # lifespan 의 엔진 생성 회피 — main import 전에 설정 (기존 파일들의 관례와 동일)

from main import app  # noqa: E402
from src.config.database import get_potato_session, get_session  # noqa: E402
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


@pytest_asyncio.fixture
async def sessionmaker():
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
        execution_options={"schema_translate_map": {"pub": None, "usr": None, "bill": None, "dist": None, "commu": None, "potato": None, "doc": None}},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    await engine.dispose()


@pytest.fixture
def social_profile():
    """로그인에 쓰일 기본 소셜 프로필 (GOOGLE/test-sub).

    다른 provider·다른 사용자가 필요하면 테스트 파일에서 동일 이름으로 재정의해 오버라이드:

        @pytest.fixture
        def social_profile():
            return SocialProfile("NAVER", "buyer-sub", "buyer@x.com", "독자")
    """
    return SocialProfile("GOOGLE", "test-sub", "test@x.com", "테스트유저")


@pytest.fixture
def order_gateway():
    """기본 결제 게이트웨이 대역 — 항상 승인(ok=True). 실패 시나리오는 로컬 재정의."""
    return FakeGateway(ok=True)


@pytest.fixture
def app_db(sessionmaker, social_profile):
    """get_session + get_auth_service(FakeProvider) 오버라이드 (기존 34개 파일의 공통 패턴).

    반환값은 sessionmaker 콜러블 — 테스트에서 `async with app_db() as s:` 로 직접 시딩/검증 가능.
    """
    async def _session():
        async with sessionmaker() as s:
            yield s

    def _auth(session: AsyncSession = Depends(get_session)):
        return AuthService(
            SqlAccountRepository(session),
            {social_profile.provider_cd: FakeProvider(social_profile.provider_cd, social_profile)},
            token_issuer(),
        )

    app.dependency_overrides[get_session] = _session
    app.dependency_overrides[get_auth_service] = _auth
    yield sessionmaker
    app.dependency_overrides.clear()


@pytest.fixture
def app_db_orders(app_db, order_gateway):
    """app_db + get_order_service 오버라이드 (기존 9개 파일의 `_order` 람다와 동일 구성:
    OrderService(SqlOrderRepository(session), gateway, SqlBookPricing(session))).
    """
    def _order(session: AsyncSession = Depends(get_session)):
        return OrderService(SqlOrderRepository(session), order_gateway, SqlBookPricing(session))

    app.dependency_overrides[get_order_service] = _order
    return app_db


@pytest.fixture
def app_db_potato(sessionmaker):
    """get_session + get_potato_session 오버라이드 — potato(운영자) 엔드포인트 테스트용
    (test_payouts_e2e.py·test_potato_auth_e2e.py 의 구성과 동일)."""
    async def _session():
        async with sessionmaker() as s:
            yield s

    app.dependency_overrides[get_session] = _session
    app.dependency_overrides[get_potato_session] = _session
    yield sessionmaker
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client(app_db):
    """app_db 오버라이드가 걸린 httpx AsyncClient — 고객 엔드포인트 E2E용 (auth/books 등)."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        yield c


@pytest_asyncio.fixture
async def client_orders(app_db_orders):
    """app_db_orders 오버라이드가 걸린 httpx AsyncClient — 주문/결제 흐름 포함 E2E용."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        yield c
