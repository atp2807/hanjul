"""conftest 공용 픽스처(client·client_orders·app_db_potato 등) 회귀 가드.

목적: tests/integration/conftest.py 에 새로 추가한 공용 픽스처(app_db/app_db_orders/
app_db_potato/client/client_orders)와 book_helpers·order_helpers 가 실제로 동작하는지
증명. 이 파일이 깨지면 신규 픽스처/헬퍼가 다른 테스트에 배선되기 전에 여기서 먼저 잡힌다.
"""
from src.features.potato.application.password import hash_password
from src.features.potato.domain.models import DEVELOPER
from src.features.potato.infrastructure.operator_repo import SqlOperatorRepository

from tests.integration.auth_helpers import login_account
from tests.integration.book_helpers import create_book, publish_priced_book
from tests.integration.order_helpers import buy_book


async def test_client_fixture_login_and_create_book(client):
    """client 픽스처(app_db 오버라이드 걸린 httpx AsyncClient) — 로그인 → 책 생성."""
    token, me = await login_account(client, "google", "x")
    assert me["email"] == "test@x.com"
    headers = {"Authorization": f"Bearer {token}"}

    book_id = await create_book(client, headers, title="스모크북")
    content = (await client.get(f"/api/books/{book_id}/content", headers=headers)).json()
    assert content["title"] == "스모크북"


async def test_client_orders_fixture_full_purchase_flow(client_orders):
    """client_orders 픽스처 — publish_priced_book + buy_book 헬퍼로 구매 1회 성공 확인."""
    token, _ = await login_account(client_orders, "google", "x")
    headers = {"Authorization": f"Bearer {token}"}

    book_id = await publish_priced_book(
        client_orders, headers, title="스모크유료책", price=3000, raw_text="1\n\n2"
    )
    order_id = await buy_book(client_orders, headers, book_id)
    assert order_id

    order = (await client_orders.get(f"/api/orders/{order_id}", headers=headers)).json()
    assert order["status"] == "PAID"

    # 구매 후 전체 열람 가능 (가격이 매겨진 책 + 본인 소유)
    content = (await client_orders.get(f"/api/books/{book_id}/content", headers=headers)).json()
    assert content["isPreview"] is False


async def test_app_db_potato_fixture_operator_login(app_db_potato):
    """app_db_potato 픽스처 — potato 운영자 로그인 성공 확인 (get_session/get_potato_session 오버라이드)."""
    import httpx
    from main import app

    async with app_db_potato() as s:
        await SqlOperatorRepository(s).create(
            email="smoke-op@hanjul.io", name="운영자", role=DEVELOPER,
            password_hash=hash_password("smoke-pass-123"),
        )

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        r = await c.post(
            "/api/potato/auth/login",
            json={"email": "smoke-op@hanjul.io", "password": "smoke-pass-123"},
        )
        assert r.status_code == 200, r.text
        assert r.json()["role"] == "DEVELOPER"
