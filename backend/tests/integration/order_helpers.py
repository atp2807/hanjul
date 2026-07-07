"""주문(orders) 생성·결제확인 테스트 헬퍼 — auth_helpers.py 와 동일한 스타일.

엔드포인트 계약은 src/features/billing/presentation/{schemas,endpoints}.py 실측:
POST /api/orders 는 청약철회 동의(withdrawalConsent) 없으면 422 (전자상거래법 §17⑥),
금액은 클라가 못 보내고 서버가 책 가격에서 도출한다.
"""


async def buy_book(client, headers, book_id: str, *, channel: str = "SELF", pg_tx_id: str = "test-tx") -> str:
    """POST /api/orders → POST /api/orders/{id}/confirm 2-스텝 구매. order_id 반환."""
    r = await client.post(
        "/api/orders",
        json={"bookId": book_id, "channel": channel, "withdrawalConsent": True},
        headers=headers,
    )
    assert r.status_code == 201, r.text
    order_id = r.json()["id"]

    r = await client.post(f"/api/orders/{order_id}/confirm", json={"pgTxId": pg_tx_id}, headers=headers)
    assert r.status_code == 200, r.text

    return order_id
