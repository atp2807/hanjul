"""desktop/store.py(SQLite Host Port v0) 단위 테스트.

각 테스트는 tmp_path 로 격리된 sqlite 파일을 써서 desktop/data/ide.db(실사용 데이터)를
건드리지 않는다.
"""

import pytest

from store import DEFAULT_BOOK_TITLE, DEFAULT_CHAPTER_TITLE, Store


@pytest.fixture
def store(tmp_path):
    return Store(tmp_path / "ide.db")


def test_seed_creates_default_book_and_chapter(store):
    book = store.get_book()
    assert book["title"] == DEFAULT_BOOK_TITLE
    assert set(book.keys()) == {"id", "title"}

    chapters = store.list_chapters()
    assert len(chapters) == 1
    assert chapters[0]["title"] == DEFAULT_CHAPTER_TITLE
    assert chapters[0]["status"] == "DRAFT"
    assert chapters[0]["synopsis"] == ""


def test_seed_is_idempotent_across_reopen(tmp_path):
    db_path = tmp_path / "ide.db"
    Store(db_path)
    Store(db_path)  # 재오픈 — 시드가 중복 생성되면 안 됨
    store3 = Store(db_path)
    assert len(store3.list_chapters()) == 1


def test_list_chapters_excludes_html_field(store):
    chapters = store.list_chapters()
    assert "html" not in chapters[0]


def test_load_chapter_includes_html_field(store):
    chapter_id = store.list_chapters()[0]["id"]
    loaded = store.load_chapter(chapter_id)
    assert "data-juldoc" in loaded["html"]


def test_load_chapter_missing_id_raises(store):
    with pytest.raises(ValueError):
        store.load_chapter(999999)


def test_create_chapter_appends_at_end_with_defaults(store):
    result = store.create_chapter("2장")
    assert "id" in result

    chapters = store.list_chapters()
    assert len(chapters) == 2
    assert chapters[-1]["id"] == result["id"]
    assert chapters[-1]["title"] == "2장"
    assert chapters[-1]["status"] == "DRAFT"
    assert chapters[-1]["synopsis"] == ""

    loaded = store.load_chapter(result["id"])
    assert "data-juldoc" in loaded["html"]


def test_save_chapter_partial_update_preserves_other_fields(store):
    chapter_id = store.list_chapters()[0]["id"]

    store.save_chapter(chapter_id, {"synopsis": "발단부"})
    loaded = store.load_chapter(chapter_id)
    assert loaded["synopsis"] == "발단부"
    assert loaded["title"] == DEFAULT_CHAPTER_TITLE  # 안 건드린 필드 보존

    result = store.save_chapter(chapter_id, {"html": '<article data-juldoc="1"><p>본문</p></article>'})
    assert "savedAt" in result

    loaded2 = store.load_chapter(chapter_id)
    assert loaded2["synopsis"] == "발단부"  # 이전 patch 보존
    assert "본문" in loaded2["html"]


def test_save_chapter_status_round_trips_via_status_field(store):
    chapter_id = store.list_chapters()[0]["id"]
    store.save_chapter(chapter_id, {"status": "REVISING"})
    assert store.load_chapter(chapter_id)["status"] == "REVISING"


def test_reorder_chapters_changes_list_order(store):
    c2 = store.create_chapter("2장")
    c3 = store.create_chapter("3장")
    first_id = store.list_chapters()[0]["id"]

    new_order = [c3["id"], first_id, c2["id"]]
    result = store.reorder_chapters(new_order)
    assert result["ok"] is True

    ids = [c["id"] for c in store.list_chapters()]
    assert ids == new_order


def test_delete_chapter_removes_it(store):
    c2 = store.create_chapter("2장")
    result = store.delete_chapter(c2["id"])
    assert result["ok"] is True

    ids = [c["id"] for c in store.list_chapters()]
    assert c2["id"] not in ids


def test_delete_chapter_is_idempotent_for_missing_id(store):
    result = store.delete_chapter(999999)
    assert result["ok"] is True
