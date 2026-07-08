"""desktop/backup.py(P1 슬라이스7, 백업 push) 단위 테스트.

publisher.py 테스트(test_publisher.py)와 동일하게 stdlib http.server 기반 Fake 서버로
요청 계약(경로·Bearer·바디)을 실측 단언한다. 진짜 백엔드는 띄우지 않는다.
"""
import hashlib
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from backup import backup_now
from publisher import PublishHttpError
from store import Store


# ── Fake 서버 — PUT /api/manuscripts/{syncKey} 하나만 안다 ──────────────────


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
        status, payload = self.server.responder(self.command, self.path, body)
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
    """responder(method, path, body) -> (status, json_payload_or_None) 를 받아 그대로 응답."""

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


def _echo_saved_responder(method, path, body):
    """모든 챕터를 "저장됨"으로 응답하는 기본 responder — 요청 계약 검증용."""
    return 200, {"savedCount": len(body["chapters"]), "skippedCount": 0}


@pytest.fixture
def store(tmp_path):
    return Store(tmp_path / "ide.db")


@pytest.fixture
def fake_server():
    server = FakeServer(_echo_saved_responder)
    yield server
    server.stop()


# ── 요청 계약 ────────────────────────────────────────────────────────────


def test_backup_now_pushes_seed_chapter_with_sync_key_and_hash(store, fake_server):
    sync_key = store.get_sync_key()
    assert sync_key  # __init__ 시점에 이미 채워져 있어야 함(store.py _ensure_sync_key)

    result = backup_now(store, {"apiBase": fake_server.base_url, "token": "tok-123"})

    assert result == {"savedCount": 1, "skippedCount": 0}
    reqs = fake_server.requests
    assert len(reqs) == 1
    assert reqs[0]["method"] == "PUT"
    assert reqs[0]["path"] == f"/api/manuscripts/{sync_key}"
    assert reqs[0]["authorization"] == "Bearer tok-123"
    assert reqs[0]["content_type"] == "application/json"

    body = reqs[0]["body"]
    assert body["title"] == store.get_book()["title"]
    assert len(body["chapters"]) == 1

    seed = store.list_chapters()[0]
    full = store.load_chapter(seed["id"])
    chapter = body["chapters"][0]
    assert chapter["chapterKey"] == str(seed["id"])
    assert chapter["title"] == seed["title"]
    assert chapter["html"] == full["html"]
    assert chapter["contentHash"] == hashlib.sha256(full["html"].encode("utf-8")).hexdigest()


def test_backup_now_sends_every_local_chapter(store, fake_server):
    store.create_chapter("2장")
    store.create_chapter("3장")

    result = backup_now(store, {"apiBase": fake_server.base_url, "token": "tok"})

    assert result == {"savedCount": 3, "skippedCount": 0}
    body = fake_server.requests[0]["body"]
    assert [c["title"] for c in body["chapters"]] == ["1장", "2장", "3장"]


def test_backup_now_without_token_omits_authorization_header(store, fake_server):
    backup_now(store, {"apiBase": fake_server.base_url, "token": None})
    assert fake_server.requests[0]["authorization"] is None


# ── dedup — 서버 판단을 그대로 전달(로컬에서 미리 거르지 않음) ───────────────


def test_backup_now_surfaces_server_dedup_skip_counts(store):
    """실제 dedup 판정은 서버(manuscript_repo.push_chapter)가 한다 — 이 모듈은 매번 전체
    챕터를 그대로 보내고, 서버가 돌려준 savedCount/skippedCount 를 있는 그대로 반환한다."""

    def responder(method, path, body):
        return 200, {"savedCount": 0, "skippedCount": len(body["chapters"])}

    server = FakeServer(responder)
    try:
        result = backup_now(store, {"apiBase": server.base_url, "token": "tok"})
    finally:
        server.stop()

    assert result == {"savedCount": 0, "skippedCount": 1}


# ── 실패 전파(삼키지 않음 — 삼키는 책임은 app.py 호출자) ─────────────────────


def test_backup_now_surfaces_server_http_error(store):
    def responder(method, path, body):
        return 401, {"detail": "인증이 필요해요."}

    server = FakeServer(responder)
    try:
        with pytest.raises(PublishHttpError) as exc_info:
            backup_now(store, {"apiBase": server.base_url, "token": "bad"})
    finally:
        server.stop()
    assert exc_info.value.status == 401


def test_backup_now_surfaces_connection_failure(store):
    with pytest.raises(PublishHttpError) as exc_info:
        backup_now(store, {"apiBase": "http://127.0.0.1:1", "token": "tok"})
    assert exc_info.value.status is None
