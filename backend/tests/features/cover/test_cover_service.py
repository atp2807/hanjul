"""CoverService — 표지 생성 후 책 연결 (Fake)."""
import uuid

import pytest

from src.features.cover.application.cover_service import CoverService
from src.features.cover.domain.ports import BookNotFound
from tests.fixtures.fake_cover import FakeCoverGenerator, FakeCoverRepository


async def test_generate_sets_cover_and_returns_url():
    repo = FakeCoverRepository()
    book_id = uuid.uuid4()
    repo.seed(book_id)
    gen = FakeCoverGenerator("https://img/x.png")
    svc = CoverService(repo, gen)

    url = await svc.generate_for_book(book_id, "잔잔한 한국 소설 표지")

    assert url == "https://img/x.png"
    assert repo.covers[book_id] == "https://img/x.png"
    assert gen.prompts == ["잔잔한 한국 소설 표지"]


async def test_generate_for_missing_book_raises():
    svc = CoverService(FakeCoverRepository(), FakeCoverGenerator())
    with pytest.raises(BookNotFound):
        await svc.generate_for_book(uuid.uuid4(), "x")
