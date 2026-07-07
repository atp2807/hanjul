"""desktop/publisher.py(P1 슬라이스4, 발행 연결) 단위 테스트.

HTTP 는 stdlib `http.server` 기반 Fake 서버로 검증한다(헥사고날 Fake 문화 그대로) —
요청 경로·메서드·헤더(Bearer)·바디를 실측 단언한다. 진짜 백엔드는 전혀 띄우지 않는다.
"""

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from publisher import preflight, publish
from store import DEFAULT_BOOK_TITLE, DEFAULT_CHAPTER_TITLE, Store


# ── Fake 서버 — book 생성/content 교체/publish-now 3개 경로만 안다 ──────────


class _FakeHandler(BaseHTTPRequestHandler):
    def log_message(self, *args):  # 테스트 출력 조용히
        pass

    def _handle(self):
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b""
        body = json.loads(raw.decode("utf-8")) if raw else None
        self.server.requests.append(
            {
                "method": self.command,
                "path": self.path,
                "authorization": self.headers.get("Authorization"),
                "content_type": self.headers.get("Content-Type"),
                "body": body,
            }
        )
        status, payload = self.server.responder(self.command, self.path)
        data = json.dumps(payload).encode("utf-8") if payload is not None else b""
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        if data:
            self.wfile.write(data)

    do_GET = _handle
    do_POST = _handle
    do_PUT = _handle
    do_DELETE = _handle


class FakeServer:
    """responder(method, path) -> (status, json_payload_or_None) 를 받아 그대로 응답."""

    def __init__(self, responder):
        self.httpd = HTTPServer(("127.0.0.1", 0), _FakeHandler)
        self.httpd.requests = []
        self.httpd.responder = responder
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    @property
    def requests(self):
        return self.httpd.requests

    @property
    def base_url(self):
        return f"http://127.0.0.1:{self.httpd.server_port}"

    def stop(self):
        self.httpd.shutdown()
        self.thread.join(timeout=2)


REMOTE_BOOK_ID = "11111111-1111-1111-1111-111111111111"


def _happy_responder(method, path):
    if method == "POST" and path == "/api/books":
        return 201, {"bookId": REMOTE_BOOK_ID}
    if method == "PUT" and path == f"/api/books/{REMOTE_BOOK_ID}/content":
        return 204, None
    if method == "POST" and path == f"/api/books/{REMOTE_BOOK_ID}/publish-now":
        return 204, None
    return 404, {"detail": "unexpected path in test"}  # pragma: no cover


@pytest.fixture
def store(tmp_path):
    return Store(tmp_path / "ide.db")


@pytest.fixture
def fake_server():
    server = FakeServer(_happy_responder)
    yield server
    server.stop()


# ── 프리플라이트 ──────────────────────────────────────────────────────────


def test_preflight_ok_for_default_seed_chapter(store):
    ok, chapters, violations = preflight(store)
    assert ok is True
    assert violations == []
    assert chapters == [
        {"title": DEFAULT_CHAPTER_TITLE, "blocks": [{"type": "P", "html": "<p></p>"}]}
    ]


def test_preflight_blocks_on_table_block_no_network(store, fake_server):
    """표 블록은 서버 화이트리스트 밖 — 발행 자체를 막고 네트워크 호출은 0회여야 한다."""
    chapter_id = store.list_chapters()[0]["id"]
    store.save_chapter(
        chapter_id,
        {
            "html": (
                '<article data-juldoc="1">'
                "<p>본문</p>"
                "<table><tr><td>a</td><td>b</td></tr></table>"
                "</article>"
            )
        },
    )

    ok, chapters, violations = preflight(store)
    assert ok is False
    assert chapters is None
    assert len(violations) == 1
    assert violations[0]["blockType"] == "TABLE"
    assert "알 수 없는 블록 타입" in violations[0]["reason"]

    result = publish(store, {"apiBase": fake_server.base_url, "token": "tok"})
    assert result == {"ok": False, "violations": violations}
    assert fake_server.requests == []  # 네트워크 호출 없음


def test_preflight_blocks_on_disallowed_inline_underline(store):
    """<u> 는 dialect 인라인 화이트리스트엔 있지만 서버 block_html.py 엔 없다(strong/em만)."""
    chapter_id = store.list_chapters()[0]["id"]
    store.save_chapter(
        chapter_id,
        {"html": '<article data-juldoc="1"><p>밑줄 <u>강조</u></p></article>'},
    )

    ok, chapters, violations = preflight(store)
    assert ok is False
    assert chapters is None
    assert violations[0]["blockType"] == "P"
    assert "<u>" in violations[0]["reason"]


def test_preflight_splits_on_embedded_h1(store):
    """로컬 챕터 하나의 html 안에 h1 이 더 있으면 서버 챕터 여러 개로 쪼갠다(h1 경계 유지)."""
    chapter_id = store.list_chapters()[0]["id"]
    store.save_chapter(
        chapter_id,
        {
            "html": (
                '<article data-juldoc="1">'
                "<h1>제목전</h1><p>본문A</p>"
                "<h1>다음장</h1><p>본문B</p>"
                "</article>"
            )
        },
    )

    ok, chapters, violations = preflight(store)
    assert ok is True
    assert violations == []
    assert [c["title"] for c in chapters] == ["제목전", "다음장"]
    assert chapters[0]["blocks"] == [{"type": "P", "html": "<p>본문A</p>"}]
    assert chapters[1]["blocks"] == [{"type": "P", "html": "<p>본문B</p>"}]


# ── publish() — Fake 서버 왕복 ────────────────────────────────────────────


def test_publish_creates_book_then_sets_content_then_publishes_now(store, fake_server):
    result = publish(store, {"apiBase": fake_server.base_url, "token": "test-token-123"})

    assert result == {"ok": True, "remoteBookId": REMOTE_BOOK_ID, "chapterCount": 1}

    reqs = fake_server.requests
    assert [r["method"] for r in reqs] == ["POST", "PUT", "POST"]
    assert [r["path"] for r in reqs] == [
        "/api/books",
        f"/api/books/{REMOTE_BOOK_ID}/content",
        f"/api/books/{REMOTE_BOOK_ID}/publish-now",
    ]
    # 인증 — Bearer 헤더가 세 요청 모두에 그대로 실림
    assert all(r["authorization"] == "Bearer test-token-123" for r in reqs)
    # 책 생성 바디
    assert reqs[0]["body"] == {"title": DEFAULT_BOOK_TITLE, "kind": "BOOK"}
    assert reqs[0]["content_type"] == "application/json"
    # 콘텐츠 교체 바디 — 정본 chapters 계약 그대로
    assert reqs[1]["body"] == {
        "chapters": [
            {"title": DEFAULT_CHAPTER_TITLE, "blocks": [{"type": "P", "html": "<p></p>"}]}
        ]
    }
    # 즉시출판은 바디 없음
    assert reqs[2]["body"] is None

    # store 에 remote_book_id 가 저장돼 다음 발행부터 재사용된다
    assert store.get_remote_book_id() == REMOTE_BOOK_ID


def test_publish_reuses_remote_book_id_on_second_call(store, fake_server):
    first = publish(store, {"apiBase": fake_server.base_url, "token": "tok"})
    assert first["ok"] is True
    assert len(fake_server.requests) == 3

    second = publish(store, {"apiBase": fake_server.base_url, "token": "tok"})
    assert second == {"ok": True, "remoteBookId": REMOTE_BOOK_ID, "chapterCount": 1}

    # 두 번째 발행은 책 재생성 없이 content+publish-now 2건만
    new_reqs = fake_server.requests[3:]
    assert [r["method"] for r in new_reqs] == ["PUT", "POST"]
    assert [r["path"] for r in new_reqs] == [
        f"/api/books/{REMOTE_BOOK_ID}/content",
        f"/api/books/{REMOTE_BOOK_ID}/publish-now",
    ]


def test_publish_surfaces_server_http_error(store):
    """예: 가격 미설정(PriceRequired, 422) — 서버 에러를 조용히 삼키지 않고 그대로 전달."""

    def responder(method, path):
        if method == "POST" and path == "/api/books":
            return 201, {"bookId": REMOTE_BOOK_ID}
        if method == "PUT" and path.endswith("/content"):
            return 204, None
        if method == "POST" and path.endswith("/publish-now"):
            return 422, {"detail": "출판하려면 가격을 먼저 설정해야 해요."}
        return 404, {"detail": "unexpected"}  # pragma: no cover

    server = FakeServer(responder)
    try:
        result = publish(store, {"apiBase": server.base_url, "token": "tok"})
    finally:
        server.stop()

    assert result == {
        "ok": False,
        "error": {"status": 422, "message": "출판하려면 가격을 먼저 설정해야 해요."},
    }


def test_publish_surfaces_connection_failure(store):
    """서버가 아예 안 떠 있으면(연결 실패) status=None 으로 원인을 전달한다."""
    result = publish(store, {"apiBase": "http://127.0.0.1:1", "token": "tok"})
    assert result["ok"] is False
    assert result["error"]["status"] is None
    assert result["error"]["message"]


# ── store 마이그레이션/설정 ───────────────────────────────────────────────


def test_remote_book_id_defaults_to_none(store):
    assert store.get_remote_book_id() is None


def test_set_and_get_remote_book_id_round_trips(store):
    store.set_remote_book_id(REMOTE_BOOK_ID)
    assert store.get_remote_book_id() == REMOTE_BOOK_ID


def test_remote_book_id_column_migration_is_idempotent(tmp_path):
    """멱등 ALTER — 이미 컬럼 있는 DB 파일을 재오픈해도 에러 없이 그대로 동작해야 한다."""
    db_path = tmp_path / "ide.db"
    Store(db_path)  # 최초 생성 — remote_book_id 컬럼 추가
    store2 = Store(db_path)  # 재오픈 — ALTER 재시도 없이 그대로 통과해야 함(에러 시 여기서 raise)
    assert store2.get_remote_book_id() is None
    store2.set_remote_book_id(REMOTE_BOOK_ID)

    store3 = Store(db_path)  # 다시 재오픈 — 저장된 값 보존 + 세 번째 재오픈도 안전
    assert store3.get_remote_book_id() == REMOTE_BOOK_ID


def test_get_settings_defaults_to_none(store):
    assert store.get_settings() == {"apiBase": None, "token": None}


def test_save_settings_partial_update_preserves_other_field(store):
    store.save_settings({"apiBase": "http://127.0.0.1:28000"})
    assert store.get_settings() == {"apiBase": "http://127.0.0.1:28000", "token": None}

    store.save_settings({"token": "abc123"})
    assert store.get_settings() == {"apiBase": "http://127.0.0.1:28000", "token": "abc123"}

    store.save_settings({"token": "xyz789"})
    assert store.get_settings() == {"apiBase": "http://127.0.0.1:28000", "token": "xyz789"}
