"""SqlBookRepository 통합 테스트 — 실 DB 엔진(SQLite)에 대해 영속성 검증."""

from src.features.books.infrastructure.book_repo import SqlBookRepository


async def test_create_and_get_content_roundtrip(sessionmaker):
    async with sessionmaker() as s:
        repo = SqlBookRepository(s)
        book_id = await repo.create_book(title="한글책", kind="WEBNOVEL", language="ko")
        await repo.add_chapter_with_blocks(
            book_id, "프롤로그",
            [{"type": "H1", "html": "<h1>제목</h1>"}, {"type": "P", "html": "<p>본문입니다.</p>"}],
        )

    # 새 세션으로 조회 → 실제 DB 에 영속됐음을 증명 (인메모리 Fake 와 차별)
    async with sessionmaker() as s2:
        content = await SqlBookRepository(s2).get_content(book_id)

    assert content is not None
    assert content.title == "한글책"
    assert content.kind == "WEBNOVEL"
    assert len(content.chapters) == 1
    blocks = content.chapters[0].blocks
    assert [b.block_type for b in blocks] == ["H1", "P"]
    assert blocks[1].html == "<p>본문입니다.</p>"


async def test_chapters_persist_in_order(sessionmaker):
    async with sessionmaker() as s:
        repo = SqlBookRepository(s)
        book_id = await repo.create_book(title="연재물", kind="WEBNOVEL", language="ko")
        await repo.add_chapter_with_blocks(book_id, "1화", [{"type": "P", "html": "<p>일</p>"}])
        await repo.add_chapter_with_blocks(book_id, "2화", [{"type": "P", "html": "<p>이</p>"}])
        await repo.add_chapter_with_blocks(book_id, "3화", [{"type": "P", "html": "<p>삼</p>"}])

    async with sessionmaker() as s2:
        content = await SqlBookRepository(s2).get_content(book_id)

    assert [c.order_no for c in content.chapters] == [0, 1, 2]
    assert [c.title for c in content.chapters] == ["1화", "2화", "3화"]


async def test_get_content_missing_returns_none(sessionmaker):
    import uuid
    async with sessionmaker() as s:
        assert await SqlBookRepository(s).get_content(uuid.uuid4()) is None
