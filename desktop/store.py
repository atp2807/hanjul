"""한줄 IDE 데스크탑 호스트 — SQLite 기반 저장소 (Host Port v0 정본 구현).

계약 전문 = packages/ide-core/HOST_PORT.md. 이 모듈은 그 계약의 Python 쪽 정본이다.

테이블(단수+접미어, CLAUDE.md 컨벤션):
    book(id, title, created_ts, updated_ts)
    chapter(id, book_id, title, synopsis, status_cd, order_no, html, created_ts, updated_ts)

컬럼 status_cd/order_no 는 DB 내부 표기일 뿐, 브리지로 나가는 dict 는 이미
HOST_PORT.md 규칙(camelCase, _cd 벗김, _no 비노출)을 따른다 — status_cd → "status",
order_no 는 아예 노출하지 않고 배열 순서로만 표현한다.

호출마다 짧은 연결을 열고 닫는다: pywebview 는 js_api 메서드를 호출마다 별도 스레드에서
실행하므로(lr-9a45e6e4) 커넥션을 오래 공유하지 않는 편이 스레드 안전을 가장 단순하게
확보하는 방법이다. SQLite 파일 잠금이 동시 쓰기를 직렬화해준다(단일 사용자 로컬 앱
스케일에 충분).
"""

import sqlite3
import time
from contextlib import contextmanager
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


def _now_iso():
    return time.strftime("%Y-%m-%dT%H:%M:%S")


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


class Store:
    """Host Port v0 의 7개 메서드(getBook/listChapters/loadChapter/saveChapter/
    createChapter/deleteChapter/reorderChapters 에 각각 대응)를 SQLite 위에 구현.
    첫 생성 시 book 1개 + 빈 챕터 1개를 멱등하게 시드한다.
    """

    def __init__(self, db_path=DEFAULT_DB_PATH):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
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
                """
            )

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
        now = _now_iso()
        set_clauses.append("updated_ts = ?")
        values.append(now)
        values.append(chapter_id)
        with self._session() as conn:
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
