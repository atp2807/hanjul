"""한줄 IDE 데스크탑 — 시스템 브라우저 로그인 플로우(RFC 8252). P1 슬라이스5.

지금까지의 "토큰 수동 붙여넣기"(``app.js`` 설정 다이얼로그의 prompt) 대신, 데스크탑 표준
패턴대로:

    1) 127.0.0.1 임시 포트에 1회용 HTTP 리스너를 연다(``start_loopback_listener``).
    2) 백엔드에서 실제 Google 인가 URL을 받아(``build_authorization_url(redirect_uri)``)
       시스템 브라우저로 연다.
    3) 브라우저가 Google 로그인 → 백엔드 콜백을 거쳐 최종적으로 그 루프백 주소로
       리다이렉트되면, 리스너가 쿼리스트링(``?token=...&isNew=...``)을 받아 파싱한다
       (``backend/src/features/auth/presentation/endpoints.py`` 의 ``next``/``_redirect`` —
       루프백은 fragment를 못 받아 쿼리스트링을 쓴다).

``run_login_flow()`` 가 전체를 오케스트레이션한다. ``build_authorization_url``/
``open_browser`` 를 인자로 받게 해 실제 백엔드·브라우저 없이도(가짜 콜백으로) 리스너
로직만 결정적으로 테스트할 수 있게 했다(desktop/tests/test_auth_flow.py).

주의: favicon.ico 등 브라우저가 보낼 수 있는 잡음 요청은 ``/callback`` 경로가 아니면
무시하고 계속 대기한다(진짜 콜백 도착 전까지) — "1회 수신 후 종료"는 정확히는
"올바른 콜백을 1회 수신하면 종료"를 뜻한다.
"""

from __future__ import annotations

import http.server
import queue
import time
import webbrowser
from urllib.parse import parse_qs, urlparse

_SUCCESS_HTML = """<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><title>한줄 IDE 로그인</title></head>
<body style="font-family: sans-serif; text-align: center; padding-top: 4rem;">
  <p>로그인 완료 — 이 창은 닫아도 됩니다.</p>
</body></html>
"""


class LoginTimeoutError(Exception):
    """지정 시간 안에 콜백을 받지 못함(사용자가 브라우저에서 로그인을 완료하지 않음 등)."""


class LoginCallbackError(Exception):
    """콜백은 왔지만 에러 파라미터를 담고 있거나(사용자 취소 등) 토큰이 없음."""

    def __init__(self, error: str):
        self.error = error
        super().__init__(f"OAuth 콜백 에러: {error}")


def _make_handler(result_queue: "queue.Queue[dict]"):
    class _CallbackHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802 (BaseHTTPRequestHandler 관례)
            parsed = urlparse(self.path)
            if parsed.path != "/callback":
                # favicon.ico 등 잡음 요청 — 콜백으로 취급하지 않고 404만 응답.
                # (result_queue 에 아무것도 넣지 않으므로 wait_for_callback 이 계속 대기한다)
                self.send_response(404)
                self.end_headers()
                return
            params = parse_qs(parsed.query)
            body = _SUCCESS_HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            result_queue.put(params)

        def log_message(self, format, *args):  # noqa: A002 (stdlib 시그니처 그대로)
            pass  # 콘솔 스팸 방지 — 요청 로그는 필요 없다.

    return _CallbackHandler


def start_loopback_listener():
    """127.0.0.1 임시 포트(OS가 골라줌, RFC 8252)에 리스너를 연다.

    반환: ``(server, redirect_uri, result_queue)``. ``result_queue`` 에는 ``/callback`` 요청의
    쿼리 파라미터(``parse_qs`` 결과, 즉 ``{key: [values...]}``)가 정확히 1번 들어온다.
    """
    result_queue: "queue.Queue[dict]" = queue.Queue()
    handler_cls = _make_handler(result_queue)
    server = http.server.HTTPServer(("127.0.0.1", 0), handler_cls)
    port = server.server_address[1]
    redirect_uri = f"http://127.0.0.1:{port}/callback"
    return server, redirect_uri, result_queue


def wait_for_callback(server, result_queue: "queue.Queue[dict]", timeout_s: float = 120.0) -> dict:
    """올바른 ``/callback`` 요청이 올 때까지 대기(잡음 요청은 무시하고 계속) — 전체 대기
    시간은 ``timeout_s`` 를 넘지 않는다. 콜백을 받으면(또는 타임아웃이어도) 리스너는 반드시
    닫는다(포트 누수 방지, 1회성 — 이후 같은 포트로 재사용 불가).

    반환: ``{"token": str, "isNew": bool}``. 콜백에 ``error`` 가 있으면 ``LoginCallbackError``,
    ``token`` 자체가 없으면 마찬가지로 ``LoginCallbackError("no_token")``.
    """
    deadline = time.monotonic() + timeout_s
    try:
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise LoginTimeoutError(f"{timeout_s}초 안에 로그인 콜백을 받지 못했어요.")
            server.timeout = remaining
            server.handle_request()  # remaining 초 안에 연결이 없으면 그냥 리턴(잡음/타임아웃 구분은 아래)
            try:
                params = result_queue.get_nowait()
                break
            except queue.Empty:
                continue  # favicon 등 잡음 요청이었거나 self-timeout — 데드라인 안이면 계속 대기
    finally:
        server.server_close()

    if "error" in params:
        raise LoginCallbackError(params["error"][0])
    if "token" not in params:
        raise LoginCallbackError("no_token")
    return {
        "token": params["token"][0],
        "isNew": params.get("isNew", ["0"])[0] == "1",
    }


def run_login_flow(build_authorization_url, timeout_s: float = 120.0, open_browser=webbrowser.open) -> dict:
    """전체 흐름: 리스너 오픈 → ``build_authorization_url(redirect_uri)`` 로 실제 Google 인가
    URL을 얻어 시스템 브라우저로 열기 → 콜백 대기 → ``{"token", "isNew"}`` 반환.

    ``build_authorization_url``: ``redirect_uri(str) -> authorization_url(str)``. 테스트는
    이 콜백과 ``open_browser`` 를 가짜로 주입해 실제 백엔드/브라우저 없이 오케스트레이션
    로직만 검증한다(desktop/tests/test_auth_flow.py).
    """
    server, redirect_uri, result_queue = start_loopback_listener()
    try:
        authorization_url = build_authorization_url(redirect_uri)
        open_browser(authorization_url)
        return wait_for_callback(server, result_queue, timeout_s=timeout_s)
    except Exception:
        server.server_close()  # wait_for_callback 진입 전 실패 시에도 포트는 반드시 반납
        raise
