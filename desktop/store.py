"""한줄 IDE 데스크탑 호스트 — SQLite 기반 저장소 (Host Port v0 정본 구현).

계약 전문 = packages/ide-core/HOST_PORT.md. 이 모듈은 그 계약의 Python 쪽 정본이다.

테이블(단수+접미어, CLAUDE.md 컨벤션):
    book(id, title, created_ts, updated_ts, remote_book_id)
    chapter(id, book_id, title, synopsis, status_cd, order_no, html, created_ts, updated_ts)
    setting(key, value)
    snapshot(id, chapter_id, chapter_title, html, label, created_ts)  — P1 슬라이스6, 스냅샷/되돌리기

컬럼 status_cd/order_no 는 DB 내부 표기일 뿐, 브리지로 나가는 dict 는 이미
HOST_PORT.md 규칙(camelCase, _cd 벗김, _no 비노출)을 따른다 — status_cd → "status",
order_no 는 아예 노출하지 않고 배열 순서로만 표현한다.

book.remote_book_id / setting(P1 슬라이스4, 발행 연결) — 기존 DB 파일에는 없을 수 있어
`_ensure_column()`(PRAGMA table_info 확인 후 ALTER)로 멱등 추가한다. `setting` 은
`CREATE TABLE IF NOT EXISTS` 로 충분(신규 테이블이라 컬럼 추가 이슈 없음). 발행 설정
(apiBase/token)은 `key`/`value` 두 컬럼짜리 얇은 테이블에 저장 — `get_settings()`/
`save_settings()` 참고. `snapshot` 도 완전 신규 테이블이라 같은 이유로 `CREATE TABLE
IF NOT EXISTS` 로 충분하다(컬럼 추가 마이그레이션 불필요).

snapshot 테이블은 의도적으로 `chapter_id` 에 FK 를 걸지 않는다 — "글이 안 날아간다"
안전망 원칙상 챕터가 삭제돼도 스냅샷은 남아야 하는데, `REFERENCES chapter(id)`
(ON DELETE 절 없음, 기본 NO ACTION)를 걸면 `PRAGMA foreign_keys = ON` 상태에서
delete_chapter() 가 즉시 제약 위반으로 실패한다(스냅샷이 남아있는 한 챕터 삭제가 막힘
— 정확히 원치 않는 동작). 대신 `chapter_title` 을 스냅샷 생성 시점에 그대로 복사
저장해 원본 챕터가 사라져도 스냅샷 자체는 자기완결적으로 남는다(고아 스냅샷 열람 UI는
범위 밖 — 데이터만 보존).

호출마다 짧은 연결을 열고 닫는다: pywebview 는 js_api 메서드를 호출마다 별도 스레드에서
실행하므로(lr-9a45e6e4) 커넥션을 오래 공유하지 않는 편이 스레드 안전을 가장 단순하게
확보하는 방법이다. SQLite 파일 잠금이 동시 쓰기를 직렬화해준다(단일 사용자 로컬 앱
스케일에 충분).
"""

import re
import sqlite3
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

DEFAULT_DB_PATH = Path(__file__).resolve().parent / "data" / "ide.db"

STATUSES = ("DRAFT", "REVISING", "DONE")

DEFAULT_BOOK_TITLE = "제목 없는 책"
DEFAULT_CHAPTER_TITLE = "1장"
DEFAULT_CHAPTER_HTML = '<article data-juldoc="1">\n  <p></p>\n</article>'

# saveChapter 패치가 건드릴 수 있는 필드 → (DB 컬럼, 값 그대로 통과) 매핑.
_PATCHABLE_FIELDS = {
    "title": "title",
    "synopsis": "synopsis",
    "status": "status_cd",
    "html": "html",
}

# ── 스냅샷(P1 슬라이스6) 상수 ────────────────────────────────────────────────
# 자동 스냅샷 최소 간격 — saveChapter 처리 중 해당 챕터의 최신 스냅샷이 이보다
# 오래됐으면(또는 아예 없으면) 저장 직전 상태를 자동 스냅샷(label=NULL)한다.
SNAPSHOT_AUTO_INTERVAL_S = 600  # 10분 — "세션 단위 안전망"
# 챕터당 보관 상한 — 초과 시 오래된 것부터 prune(라벨 유무 무관, 단순성 우선).
SNAPSHOT_MAX_PER_CHAPTER = 30
# 복원 직전 자동 스냅샷에 붙는 라벨(설계결정 2ⓑ).
SNAPSHOT_RESTORE_LABEL = "복원 전 자동"

_TAG_RE = re.compile(r"<[^>]+>")
_TS_FORMAT = "%Y-%m-%dT%H:%M:%S"


def _now_iso():
    return time.strftime(_TS_FORMAT)


def _parse_ts(ts):
    return datetime.strptime(ts, _TS_FORMAT)


def _strip_tags(html):
    """스냅샷 목록의 "글자수" 계산용 — 태그를 벗긴 순수 텍스트 길이. 정밀한 워드카운트가
    아니라 "이 스냅샷에 내용이 얼마나 있었나"를 가늠하는 가벼운 지표라 단순 정규식으로
    충분하다(엔진급 파서 재사용은 이 용도에 과함)."""
    return _TAG_RE.sub("", html or "")


def _chapter_row_to_summary(row):
    """listChapters 행 — html 미포함(사이드바용, 가벼움 유지)."""
    return {
        "id": row["id"],
        "title": row["title"],
        "synopsis": row["synopsis"],
        "status": row["status_cd"],
    }


def _chapter_row_to_full(row):
    """loadChapter 행 — html 포함."""
    return {**_chapter_row_to_summary(row), "html": row["html"]}


def _snapshot_row_to_summary(row):
    """listSnapshots 행 — html 미포함(목록 경량, 설계결정 4), 대신 "chars" 로 분량만."""
    return {
        "id": row["id"],
        "label": row["label"],
        "createdAt": row["created_ts"],
        "chars": len(_strip_tags(row["html"])),
    }


class Store:
    """Host Port v0 의 7개 메서드(getBook/listChapters/loadChapter/saveChapter/
    createChapter/deleteChapter/reorderChapters 에 각각 대응)를 SQLite 위에 구현.
    첫 생성 시 book 1개 + 빈 챕터 1개를 멱등하게 시드한다.
    """

    def __init__(self, db_path=DEFAULT_DB_PATH, now_fn=None):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        # now_fn 주입 — 스냅샷 10분 규칙을 sleep 없이 테스트하기 위한 클록 훅
        # (desktop/tests/test_store.py 가 고정 문자열을 반환하는 fake 를 넘긴다).
        self._now_fn = now_fn or _now_iso
        self._init_schema()
        self._ensure_seed()

    def _connect(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    @contextmanager
    def _session(self):
        """연결 하나의 수명 = 이 컨텍스트 블록. 정상 종료 시 commit, 예외 시 rollback,
        어느 쪽이든 close 로 연결을 반환한다(스레드 간 연결 공유 없음)."""
        conn = self._connect()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_schema(self):
        with self._session() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS book (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    created_ts TEXT NOT NULL,
                    updated_ts TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS chapter (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    book_id INTEGER NOT NULL REFERENCES book(id),
                    title TEXT NOT NULL,
                    synopsis TEXT NOT NULL DEFAULT '',
                    status_cd TEXT NOT NULL DEFAULT 'DRAFT',
                    order_no INTEGER NOT NULL,
                    html TEXT NOT NULL DEFAULT '',
                    created_ts TEXT NOT NULL,
                    updated_ts TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS setting (
                    key TEXT PRIMARY KEY,
                    value TEXT
                );
                CREATE TABLE IF NOT EXISTS snapshot (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chapter_id INTEGER NOT NULL,
                    chapter_title TEXT NOT NULL,
                    html TEXT NOT NULL,
                    label TEXT,
                    created_ts TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_snapshot_chapter_id ON snapshot(chapter_id);
                """
            )
            # remote_book_id — P1 슬라이스4(발행 연결). 기존 DB 파일에 멱등 추가:
            # PRAGMA table_info 로 이미 있는지 먼저 확인한 뒤에만 ALTER(재실행 시 중복 에러 방지).
            self._ensure_column(conn, "book", "remote_book_id", "TEXT")

    @staticmethod
    def _ensure_column(conn, table, column, coltype):
        cols = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
        if column not in cols:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {coltype}")

    def _ensure_seed(self):
        """첫 실행 시 기본 book 1개 + 빈 챕터 1개. 이미 book 이 있으면 아무 것도 안 한다
        (멱등 — 재실행/재오픈 시 중복 생성 금지)."""
        with self._session() as conn:
            row = conn.execute("SELECT id FROM book LIMIT 1").fetchone()
            if row is not None:
                return
            now = _now_iso()
            cur = conn.execute(
                "INSERT INTO book (title, created_ts, updated_ts) VALUES (?, ?, ?)",
                (DEFAULT_BOOK_TITLE, now, now),
            )
            book_id = cur.lastrowid
            conn.execute(
                """INSERT INTO chapter
                   (book_id, title, synopsis, status_cd, order_no, html, created_ts, updated_ts)
                   VALUES (?, ?, '', 'DRAFT', 0, ?, ?, ?)""",
                (book_id, DEFAULT_CHAPTER_TITLE, DEFAULT_CHAPTER_HTML, now, now),
            )

    def _get_book_id(self, conn):
        row = conn.execute("SELECT id FROM book ORDER BY id LIMIT 1").fetchone()
        return row["id"] if row else None

    # ── Host Port v0 ─────────────────────────────────────────────────────

    def get_book(self):
        with self._session() as conn:
            row = conn.execute("SELECT id, title FROM book ORDER BY id LIMIT 1").fetchone()
            return {"id": row["id"], "title": row["title"]}

    def list_chapters(self):
        with self._session() as conn:
            book_id = self._get_book_id(conn)
            rows = conn.execute(
                """SELECT id, title, synopsis, status_cd FROM chapter
                   WHERE book_id = ? ORDER BY order_no ASC""",
                (book_id,),
            ).fetchall()
            return [_chapter_row_to_summary(r) for r in rows]

    def load_chapter(self, chapter_id):
        with self._session() as conn:
            row = conn.execute(
                "SELECT id, title, synopsis, status_cd, html FROM chapter WHERE id = ?",
                (chapter_id,),
            ).fetchone()
            if row is None:
                raise ValueError(f"chapter {chapter_id} not found")
            return _chapter_row_to_full(row)

    def save_chapter(self, chapter_id, patch):
        patch = patch or {}
        set_clauses = []
        values = []
        for field, column in _PATCHABLE_FIELDS.items():
            if field in patch and patch[field] is not None:
                set_clauses.append(f"{column} = ?")
                values.append(patch[field])
        now = self._now_fn()
        set_clauses.append("updated_ts = ?")
        values.append(now)
        values.append(chapter_id)
        with self._session() as conn:
            # 자동 스냅샷 규칙ⓐ(설계결정 2) — 이 저장으로 덮어써지기 *직전* 상태를,
            # 해당 챕터의 최신 스냅샷이 10분보다 오래됐을 때만(또는 아예 없을 때) 남긴다.
            # patch 내용과 무관하게 "세션 단위 안전망"이라 매 saveChapter 호출마다 검사한다.
            if self._should_auto_snapshot(conn, chapter_id, now):
                row = conn.execute(
                    "SELECT title, html FROM chapter WHERE id = ?", (chapter_id,)
                ).fetchone()
                if row is not None:
                    self._insert_snapshot(conn, chapter_id, row["title"], row["html"], None, now)
            conn.execute(f"UPDATE chapter SET {', '.join(set_clauses)} WHERE id = ?", values)
        return {"savedAt": now}

    def create_chapter(self, title):
        with self._session() as conn:
            book_id = self._get_book_id(conn)
            max_row = conn.execute(
                "SELECT MAX(order_no) AS m FROM chapter WHERE book_id = ?", (book_id,)
            ).fetchone()
            next_order = (max_row["m"] if max_row["m"] is not None else -1) + 1
            now = _now_iso()
            cur = conn.execute(
                """INSERT INTO chapter
                   (book_id, title, synopsis, status_cd, order_no, html, created_ts, updated_ts)
                   VALUES (?, ?, '', 'DRAFT', ?, ?, ?, ?)""",
                (book_id, title or DEFAULT_CHAPTER_TITLE, next_order, DEFAULT_CHAPTER_HTML, now, now),
            )
            return {"id": cur.lastrowid}

    def delete_chapter(self, chapter_id):
        with self._session() as conn:
            conn.execute("DELETE FROM chapter WHERE id = ?", (chapter_id,))
        return {"ok": True}

    def reorder_chapters(self, ids):
        now = _now_iso()
        with self._session() as conn:
            for order_no, chapter_id in enumerate(ids):
                conn.execute(
                    "UPDATE chapter SET order_no = ?, updated_ts = ? WHERE id = ?",
                    (order_no, now, chapter_id),
                )
        return {"ok": True}

    def import_chapters(self, book_id, chapters):
        """원고 가져오기(P1 슬라이스3) — importer.import_manuscript() 가 만든
        ``[{"title", "html"}, ...]`` 를 기존 챕터 뒤에 order_no 를 이어 붙여 삽입한다.
        전부 커밋 1개(트랜잭션 1개) — 파일 하나 임포트가 부분 실패로 절반만 반영되지
        않는다. 반환: ``{"chapterIds": [id, ...]}`` (삽입 순서 그대로, 비어 있으면 []).
        """
        now = _now_iso()
        chapter_ids = []
        with self._session() as conn:
            max_row = conn.execute(
                "SELECT MAX(order_no) AS m FROM chapter WHERE book_id = ?", (book_id,)
            ).fetchone()
            next_order = (max_row["m"] if max_row["m"] is not None else -1) + 1
            for chapter in chapters:
                title = chapter.get("title") or DEFAULT_CHAPTER_TITLE
                html = chapter.get("html") or DEFAULT_CHAPTER_HTML
                cur = conn.execute(
                    """INSERT INTO chapter
                       (book_id, title, synopsis, status_cd, order_no, html, created_ts, updated_ts)
                       VALUES (?, ?, '', 'DRAFT', ?, ?, ?, ?)""",
                    (book_id, title, next_order, html, now, now),
                )
                chapter_ids.append(cur.lastrowid)
                next_order += 1
        return {"chapterIds": chapter_ids}

    # ── 발행 연결(P1 슬라이스4) ──────────────────────────────────────────

    def get_remote_book_id(self):
        """현재 book 이 서버에 이미 생성됐으면 그 UUID(문자열), 아니면 None."""
        with self._session() as conn:
            book_id = self._get_book_id(conn)
            row = conn.execute(
                "SELECT remote_book_id FROM book WHERE id = ?", (book_id,)
            ).fetchone()
            return row["remote_book_id"] if row else None

    def set_remote_book_id(self, remote_book_id):
        """책 생성 성공 후 서버 book UUID 를 저장(다음 발행부터는 재사용, 재생성 없음)."""
        with self._session() as conn:
            book_id = self._get_book_id(conn)
            conn.execute(
                "UPDATE book SET remote_book_id = ? WHERE id = ?", (remote_book_id, book_id)
            )
        return {"ok": True}

    def get_settings(self):
        """발행 설정(apiBase, token) 조회 — 저장된 적 없는 필드는 None."""
        with self._session() as conn:
            rows = conn.execute("SELECT key, value FROM setting").fetchall()
        values = {row["key"]: row["value"] for row in rows}
        return {"apiBase": values.get("api_base"), "token": values.get("token")}

    def save_settings(self, patch):
        """patch 에 담긴 필드(apiBase/token)만 upsert — 나머지는 보존."""
        patch = patch or {}
        field_to_key = {"apiBase": "api_base", "token": "token"}
        with self._session() as conn:
            for field, key in field_to_key.items():
                if field in patch and patch[field] is not None:
                    conn.execute(
                        """INSERT INTO setting (key, value) VALUES (?, ?)
                           ON CONFLICT(key) DO UPDATE SET value = excluded.value""",
                        (key, patch[field]),
                    )
        return {"ok": True}

    # ── 스냅샷/되돌리기(P1 슬라이스6) ────────────────────────────────────

    def _latest_snapshot_ts(self, conn, chapter_id):
        row = conn.execute(
            """SELECT created_ts FROM snapshot WHERE chapter_id = ?
               ORDER BY created_ts DESC, id DESC LIMIT 1""",
            (chapter_id,),
        ).fetchone()
        return row["created_ts"] if row else None

    def _should_auto_snapshot(self, conn, chapter_id, now):
        """최신 스냅샷이 없거나(첫 저장) SNAPSHOT_AUTO_INTERVAL_S 보다 오래됐으면 True."""
        last_ts = self._latest_snapshot_ts(conn, chapter_id)
        if last_ts is None:
            return True
        elapsed = (_parse_ts(now) - _parse_ts(last_ts)).total_seconds()
        return elapsed >= SNAPSHOT_AUTO_INTERVAL_S

    def _insert_snapshot(self, conn, chapter_id, chapter_title, html, label, now):
        """스냅샷 1건 삽입 + 상한(SNAPSHOT_MAX_PER_CHAPTER) prune 을 한 트랜잭션 안에서."""
        cur = conn.execute(
            """INSERT INTO snapshot (chapter_id, chapter_title, html, label, created_ts)
               VALUES (?, ?, ?, ?, ?)""",
            (chapter_id, chapter_title, html, label, now),
        )
        self._prune_snapshots(conn, chapter_id)
        return cur.lastrowid

    def _prune_snapshots(self, conn, chapter_id):
        """챕터당 SNAPSHOT_MAX_PER_CHAPTER 초과분을 오래된 것부터 삭제(라벨 유무 무관 —
        단순성 우선, 설계결정 3)."""
        count_row = conn.execute(
            "SELECT COUNT(*) AS c FROM snapshot WHERE chapter_id = ?", (chapter_id,)
        ).fetchone()
        excess = count_row["c"] - SNAPSHOT_MAX_PER_CHAPTER
        if excess <= 0:
            return
        old_ids = [
            r["id"]
            for r in conn.execute(
                """SELECT id FROM snapshot WHERE chapter_id = ?
                   ORDER BY created_ts ASC, id ASC LIMIT ?""",
                (chapter_id, excess),
            ).fetchall()
        ]
        conn.executemany("DELETE FROM snapshot WHERE id = ?", [(i,) for i in old_ids])

    def list_snapshots(self, chapter_id):
        """현재/과거 챕터의 스냅샷 목록 — 최신 순, html 미포함(설계결정 4)."""
        with self._session() as conn:
            rows = conn.execute(
                """SELECT id, label, created_ts, html FROM snapshot
                   WHERE chapter_id = ? ORDER BY created_ts DESC, id DESC""",
                (chapter_id,),
            ).fetchall()
            return [_snapshot_row_to_summary(r) for r in rows]

    def take_snapshot(self, chapter_id, label=None):
        """수동 스냅샷("지금 스냅샷" 버튼) — 자동 스냅샷의 10분 스로틀과 무관하게
        호출될 때마다 바로 찍는다(사용자가 명시적으로 요청한 것이라 스로틀 대상이 아님)."""
        with self._session() as conn:
            row = conn.execute(
                "SELECT title, html FROM chapter WHERE id = ?", (chapter_id,)
            ).fetchone()
            if row is None:
                raise ValueError(f"chapter {chapter_id} not found")
            now = self._now_fn()
            snapshot_id = self._insert_snapshot(conn, chapter_id, row["title"], row["html"], label, now)
        return {"id": snapshot_id}

    def restore_snapshot(self, snapshot_id):
        """스냅샷 복원 — 대상 챕터의 html 을 스냅샷 시점으로 되돌린다(title/synopsis/status는
        건드리지 않음 — 안전망의 대상은 본문이다). 복원 직전 현재 상태를 먼저 자동
        스냅샷(label=SNAPSHOT_RESTORE_LABEL, 설계결정 2ⓑ)한 뒤 덮어쓴다 — 되돌리기를
        되돌릴 수 있게. 원본 챕터가 이미 삭제됐으면(고아 스냅샷) 복원할 대상이 없으므로
        ValueError."""
        with self._session() as conn:
            snap = conn.execute(
                "SELECT chapter_id, html FROM snapshot WHERE id = ?", (snapshot_id,)
            ).fetchone()
            if snap is None:
                raise ValueError(f"snapshot {snapshot_id} not found")
            chapter_id = snap["chapter_id"]
            chapter_row = conn.execute(
                "SELECT title, html FROM chapter WHERE id = ?", (chapter_id,)
            ).fetchone()
            if chapter_row is None:
                raise ValueError(f"chapter {chapter_id} not found (원본 챕터가 삭제돼 복원 불가)")
            now = self._now_fn()
            self._insert_snapshot(
                conn, chapter_id, chapter_row["title"], chapter_row["html"], SNAPSHOT_RESTORE_LABEL, now
            )
            conn.execute(
                "UPDATE chapter SET html = ?, updated_ts = ? WHERE id = ?",
                (snap["html"], now, chapter_id),
            )
            restored = conn.execute(
                "SELECT id, title, synopsis, status_cd, html FROM chapter WHERE id = ?",
                (chapter_id,),
            ).fetchone()
            return _chapter_row_to_full(restored)
