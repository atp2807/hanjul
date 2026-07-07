"""LocalStorage 단위 테스트 — 파일 왕복 + 경로 조작 차단. (juldoc 이식)"""
import pytest
from src.features.doc.infrastructure.storage_local import LocalStorage


@pytest.fixture
def storage(tmp_path) -> LocalStorage:
    return LocalStorage(tmp_path)


async def test_put_get_roundtrip(storage):
    await storage.put("abc.png", b"HELLO", "image/png")
    assert await storage.get("abc.png") == b"HELLO"


async def test_exists(storage):
    assert await storage.exists("x.png") is False
    await storage.put("x.png", b"Y", "image/png")
    assert await storage.exists("x.png") is True


async def test_get_missing_returns_none(storage):
    assert await storage.get("missing.png") is None


def test_url_for_is_relative(storage):
    assert storage.url_for("abc.png") == "/media/abc.png"
    assert "://" not in storage.url_for("abc.png")  # 엔드포인트가 로컬 프록시로 판정


async def test_path_traversal_rejected_on_put(storage):
    with pytest.raises(ValueError):
        await storage.put("../escape.png", b"X", "image/png")


async def test_path_traversal_get_returns_none(storage):
    assert await storage.get("../../etc/passwd") is None
    assert await storage.get("sub/dir.png") is None  # 슬래시 포함 key 거부
