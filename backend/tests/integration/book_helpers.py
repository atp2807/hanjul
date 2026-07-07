"""책 생성·원고 import·즉시출판 테스트 헬퍼 — auth_helpers.py 와 동일한 스타일.

기존 테스트 파일들의 인라인 호출(POST /api/books, /import, /price, /publish-now)을
공용 함수로 뽑았다. 엔드포인트 계약은 src/features/books/presentation/endpoints.py,
src/features/catalog/presentation/endpoints.py 실측.
"""


async def create_book(client, headers=None, *, title: str, kind: str = "BOOK") -> str:
    """POST /api/books → bookId. (headers 없으면 미로그인 생성 — 대부분은 작가 인증 필요)"""
    r = await client.post("/api/books", json={"title": title, "kind": kind}, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()["bookId"]


async def import_raw(client, book_id: str, raw_text: str, headers=None) -> dict:
    """POST /api/books/{id}/import → {chapterId, blockCount} 그대로 반환."""
    r = await client.post(f"/api/books/{book_id}/import", json={"rawText": raw_text}, headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


async def publish_priced_book(
    client, headers, *, title: str, price: int, raw_text: str = "1\n\n2\n\n3"
) -> str:
    """생성 → import → 가격설정 → 즉시출판(publish-now, 심사 생략)까지 한 번에. bookId 반환."""
    book_id = await create_book(client, headers, title=title, kind="BOOK")
    await import_raw(client, book_id, raw_text, headers)
    r = await client.put(f"/api/books/{book_id}/price", json={"amount": price}, headers=headers)
    assert r.status_code == 204, r.text
    r = await client.post(f"/api/books/{book_id}/publish-now", headers=headers)
    assert r.status_code == 204, r.text
    return book_id
