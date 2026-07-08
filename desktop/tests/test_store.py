"""desktop/store.py(SQLite Host Port v0) 단위 테스트.

각 테스트는 tmp_path 로 격리된 sqlite 파일을 써서 desktop/data/ide.db(실사용 데이터)를
건드리지 않는다.
"""

import sqlite3

import pytest

from store import DEFAULT_BOOK_TITLE, DEFAULT_CHAPTER_TITLE, SNAPSHOT_MAX_PER_CHAPTER, Store


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


def test_import_chapters_appends_after_existing_with_continuing_order(store):
    book_id = store.get_book()["id"]
    assert len(store.list_chapters()) == 1  # 시드 챕터 1개

    result = store.import_chapters(
        book_id,
        [
            {"title": "가져온 1장", "html": '<article data-juldoc="1"><p>본문1</p></article>'},
            {"title": "가져온 2장", "html": '<article data-juldoc="1"><p>본문2</p></article>'},
        ],
    )
    assert len(result["chapterIds"]) == 2

    chapters = store.list_chapters()
    assert len(chapters) == 3  # 시드 1 + 가져온 2
    assert [c["title"] for c in chapters[-2:]] == ["가져온 1장", "가져온 2장"]
    assert [c["id"] for c in chapters[-2:]] == result["chapterIds"]

    loaded_first = store.load_chapter(result["chapterIds"][0])
    assert "본문1" in loaded_first["html"]
    loaded_second = store.load_chapter(result["chapterIds"][1])
    assert "본문2" in loaded_second["html"]


def test_import_chapters_continues_order_after_existing_manual_chapters(store):
    book_id = store.get_book()["id"]
    store.create_chapter("수동 2장")  # order_no 1

    result = store.import_chapters(
        book_id,
        [{"title": "가져온 장", "html": '<article data-juldoc="1"></article>'}],
    )

    ids = [c["id"] for c in store.list_chapters()]
    assert ids[-1] == result["chapterIds"][0]  # 맨 뒤에 이어붙음


def test_import_chapters_empty_list_is_noop(store):
    book_id = store.get_book()["id"]
    result = store.import_chapters(book_id, [])

    assert result["chapterIds"] == []
    assert len(store.list_chapters()) == 1


# ── 스냅샷/되돌리기(P1 슬라이스6) ─────────────────────────────────────────


def _raw_snapshots(db_path, chapter_id):
    """summary(list_snapshots)는 html 을 안 실어줘서, "저장 직전 어떤 내용이 찍혔나"를
    확인하려면 파일을 직접 열어 봐야 한다 — 테스트 전용 헬퍼."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT html, label, created_ts FROM snapshot WHERE chapter_id = ? ORDER BY id",
        (chapter_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def _clock_store(tmp_path, start="2026-01-01T00:00:00"):
    """now_fn 을 딕셔너리로 넘겨 sleep 없이 "시간 경과"를 흉내낸다 — clock["t"] 를
    테스트에서 직접 갱신하면 다음 호출부터 그 시각으로 관측된다."""
    clock = {"t": start}
    store = Store(tmp_path / "ide.db", now_fn=lambda: clock["t"])
    return store, clock


def test_snapshot_table_creation_is_idempotent_across_reopen(tmp_path):
    db_path = tmp_path / "ide.db"
    Store(db_path)
    Store(db_path)  # 재오픈 — CREATE TABLE IF NOT EXISTS 반복돼도 에러 없어야 함
    store3 = Store(db_path)
    chapter_id = store3.list_chapters()[0]["id"]
    assert store3.list_snapshots(chapter_id) == []


def test_save_chapter_first_save_takes_auto_snapshot_since_none_exists(tmp_path):
    store, _clock = _clock_store(tmp_path)
    chapter_id = store.list_chapters()[0]["id"]

    store.save_chapter(chapter_id, {"html": '<article data-juldoc="1"><p>v1</p></article>'})

    snaps = store.list_snapshots(chapter_id)
    assert len(snaps) == 1
    assert snaps[0]["label"] is None  # 자동 스냅샷은 라벨 없음


def test_save_chapter_auto_snapshot_respects_10min_throttle(tmp_path):
    store, clock = _clock_store(tmp_path)
    chapter_id = store.list_chapters()[0]["id"]

    store.save_chapter(chapter_id, {"html": '<article data-juldoc="1"><p>v1</p></article>'})
    assert len(store.list_snapshots(chapter_id)) == 1  # 최초 자동 스냅샷

    clock["t"] = "2026-01-01T00:09:00"  # +9분 — 아직 10분 안 지남
    store.save_chapter(chapter_id, {"html": '<article data-juldoc="1"><p>v2</p></article>'})
    assert len(store.list_snapshots(chapter_id)) == 1  # 추가 자동 스냅샷 없음

    clock["t"] = "2026-01-01T00:20:00"  # +11분(직전 스냅샷 대비) — 경과
    store.save_chapter(chapter_id, {"html": '<article data-juldoc="1"><p>v3</p></article>'})
    snaps = store.list_snapshots(chapter_id)
    assert len(snaps) == 2  # 저장 직전(v2) 상태가 새로 자동 스냅샷됨

    # 방금 새로 찍힌 자동 스냅샷의 실제 내용은 "저장 직전" v2 여야 한다(v3 아님).
    raw = _raw_snapshots(tmp_path / "ide.db", chapter_id)
    assert raw[-1]["label"] is None
    assert "v2" in raw[-1]["html"]

    current = store.load_chapter(chapter_id)
    assert "v3" in current["html"]  # 저장 자체는 정상 반영됨


def test_take_snapshot_is_not_throttled_by_10min_rule(tmp_path):
    """수동 스냅샷("지금 스냅샷")은 자동 스로틀과 무관하게 매번 찍힌다."""
    store, _clock = _clock_store(tmp_path)
    chapter_id = store.list_chapters()[0]["id"]

    store.take_snapshot(chapter_id, "라벨1")
    store.take_snapshot(chapter_id, "라벨2")  # 같은 시각이어도 스로틀 없이 추가됨

    snaps = store.list_snapshots(chapter_id)
    assert len(snaps) == 2
    assert {s["label"] for s in snaps} == {"라벨1", "라벨2"}


def test_take_snapshot_missing_chapter_raises(store):
    with pytest.raises(ValueError):
        store.take_snapshot(999999)


def test_list_snapshots_excludes_html_and_reports_char_count(store):
    chapter_id = store.list_chapters()[0]["id"]
    store.save_chapter(chapter_id, {"html": '<article data-juldoc="1"><p>본문내용</p></article>'})
    store.take_snapshot(chapter_id, "체크포인트")

    snaps = store.list_snapshots(chapter_id)
    assert set(snaps[0].keys()) == {"id", "label", "createdAt", "chars"}
    assert "html" not in snaps[0]
    assert snaps[0]["chars"] > 0  # 태그 벗긴 텍스트 길이


def test_list_snapshots_orders_most_recent_first(tmp_path):
    store, clock = _clock_store(tmp_path)
    chapter_id = store.list_chapters()[0]["id"]

    first = store.take_snapshot(chapter_id, "첫번째")
    clock["t"] = "2026-01-01T00:05:00"
    second = store.take_snapshot(chapter_id, "두번째")

    ids = [s["id"] for s in store.list_snapshots(chapter_id)]
    assert ids == [second["id"], first["id"]]


def test_restore_snapshot_reverts_html_and_takes_pre_restore_auto_snapshot(store):
    chapter_id = store.list_chapters()[0]["id"]
    store.save_chapter(chapter_id, {"html": '<article data-juldoc="1"><p>원본</p></article>'})
    snap = store.take_snapshot(chapter_id, "체크포인트")
    store.save_chapter(chapter_id, {"html": '<article data-juldoc="1"><p>수정본</p></article>'})

    restored = store.restore_snapshot(snap["id"])

    assert "원본" in restored["html"]
    current = store.load_chapter(chapter_id)
    assert "원본" in current["html"]  # DB에도 실제 반영됨

    labels = [s["label"] for s in store.list_snapshots(chapter_id)]
    assert "복원 전 자동" in labels  # 설계결정 2ⓑ — 복원 직전 상태도 스냅샷으로 남음


def test_restore_snapshot_preserves_title_and_only_reverts_html(store):
    """복원 대상은 본문(html)뿐 — title/synopsis/status 는 건드리지 않는다."""
    chapter_id = store.list_chapters()[0]["id"]
    snap = store.take_snapshot(chapter_id, "체크포인트")
    store.save_chapter(chapter_id, {"title": "바뀐 제목", "status": "REVISING"})

    store.restore_snapshot(snap["id"])

    current = store.load_chapter(chapter_id)
    assert current["title"] == "바뀐 제목"
    assert current["status"] == "REVISING"


def test_restore_snapshot_missing_id_raises(store):
    with pytest.raises(ValueError):
        store.restore_snapshot(999999)


def test_restore_snapshot_raises_if_chapter_already_deleted(store):
    chapter_id = store.list_chapters()[0]["id"]
    snap = store.take_snapshot(chapter_id, "삭제전")
    store.delete_chapter(chapter_id)

    with pytest.raises(ValueError):
        store.restore_snapshot(snap["id"])


def test_snapshot_survives_chapter_deletion(store):
    """설계결정 1 — FK cascade 없음: 챕터가 삭제돼도 스냅샷 행은 남는다."""
    chapter_id = store.list_chapters()[0]["id"]
    store.take_snapshot(chapter_id, "삭제전 기록")

    result = store.delete_chapter(chapter_id)
    assert result["ok"] is True

    snaps = store.list_snapshots(chapter_id)
    assert len(snaps) == 1
    assert snaps[0]["label"] == "삭제전 기록"


def test_snapshots_prune_beyond_max_per_chapter(store):
    chapter_id = store.list_chapters()[0]["id"]
    created_ids = [store.take_snapshot(chapter_id, f"s{i}")["id"] for i in range(SNAPSHOT_MAX_PER_CHAPTER + 5)]

    snaps = store.list_snapshots(chapter_id)
    assert len(snaps) == SNAPSHOT_MAX_PER_CHAPTER

    kept_ids = {s["id"] for s in snaps}
    assert kept_ids == set(created_ids[-SNAPSHOT_MAX_PER_CHAPTER:])  # 최신 것만 유지
    assert kept_ids.isdisjoint(created_ids[:5])  # 가장 오래된 것들은 제거됨


def test_snapshots_prune_scoped_per_chapter(store):
    """상한은 챕터별로 독립 — 다른 챕터의 스냅샷 개수가 이 챕터의 prune에 영향 없음."""
    chapter_a = store.list_chapters()[0]["id"]
    chapter_b = store.create_chapter("2장")["id"]

    for i in range(SNAPSHOT_MAX_PER_CHAPTER + 3):
        store.take_snapshot(chapter_a, f"a{i}")
    store.take_snapshot(chapter_b, "b0")

    assert len(store.list_snapshots(chapter_a)) == SNAPSHOT_MAX_PER_CHAPTER
    assert len(store.list_snapshots(chapter_b)) == 1
