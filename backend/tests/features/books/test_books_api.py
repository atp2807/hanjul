"""books API 엔드포인트 테스트 (FastAPI TestClient + DI 오버라이드, DB 불필요).

서비스 의존성을 인메모리 Fake repo 로 교체 → 표현+애플리케이션 배선만 검증.
"""
import pytest
from fastapi.testclient import TestClient

from src.config.settings import settings

# 테스트는 DEBUG off — lifespan 의 DB 엔진 생성/테이블 생성 스킵
settings.DEBUG = False

from main import app  # noqa: E402
from src.features.billing.application.order_service import OrderService  # noqa: E402
from src.features.billing.presentation.dependencies import get_order_service  # noqa: E402
from src.features.books.application.book_service import BookService  # noqa: E402
from src.features.books.presentation.dependencies import get_book_service  # noqa: E402
from tests.fixtures.fake_book_repo import FakeBookRepository  # noqa: E402
from tests.fixtures.fake_order_repo import FakeGateway, FakeOrderRepository, FakePricing  # noqa: E402


@pytest.fixture
def client():
    repo = FakeBookRepository()
    app.dependency_overrides[get_book_service] = lambda: BookService(repo)
    # content 엔드포인트가 entitlement(owns) 위해 order_service 에 의존 → Fake 주입
    app.dependency_overrides[get_order_service] = lambda: OrderService(
        FakeOrderRepository(), FakeGateway(), FakePricing()
    )
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_create_book(client):
    r = client.post("/api/books", json={"title": "한줄 이야기", "kind": "WEBNOVEL"})
    assert r.status_code == 201
    assert "bookId" in r.json()  # camelCase 출력


def test_import_and_get_content_camelcase(client):
    book_id = client.post("/api/books", json={"title": "책"}).json()["bookId"]

    imp = client.post(f"/api/books/{book_id}/import", json={"rawText": "# 1장\n\n한글 문단입니다."})
    assert imp.status_code == 200
    body = imp.json()
    assert body["blockCount"] == 2
    assert "chapterId" in body

    content = client.get(f"/api/books/{book_id}/content").json()
    assert content["title"] == "책"
    blocks = content["chapters"][0]["blocks"]
    assert blocks[0]["blockType"] == "H1"
    assert blocks[0]["html"] == "<h1>1장</h1>"
    assert blocks[1]["html"] == "<p>한글 문단입니다.</p>"


def test_import_unknown_book_404(client):
    import uuid
    r = client.post(f"/api/books/{uuid.uuid4()}/import", json={"rawText": "x"})
    assert r.status_code == 404


def test_get_content_unknown_404(client):
    import uuid
    r = client.get(f"/api/books/{uuid.uuid4()}/content")
    assert r.status_code == 404
