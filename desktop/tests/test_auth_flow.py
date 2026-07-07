"""desktop/auth_flow.py(P1 슬라이스5, 시스템 브라우저 로그인) 단위 테스트.

실 소켓(127.0.0.1)으로 리스너를 열고 진짜 HTTP 요청을 쏴서 검증한다 — 백엔드/브라우저는
전혀 띄우지 않는다(가짜 리다이렉트 hit). keyring은 이 모듈과 무관(token_store.py 담당,
별도 테스트 파일 test_token_store.py).
"""

import threading
import time
import urllib.error
import urllib.request

import pytest

from auth_flow import (
    LoginCallbackError,
    LoginTimeoutError,
    run_login_flow,
    start_loopback_listener,
    wait_for_callback,
)


def _fire_after(delay_s, url):
    """짧은 지연 후 GET 요청 1회 — 브라우저의 최종 리다이렉트 도착을 흉내낸다."""

    def _go():
        time.sleep(delay_s)
        urllib.request.urlopen(url, timeout=5)

    t = threading.Thread(target=_go, daemon=True)
    t.start()
    return t


def test_redirect_uri_is_loopback_with_callback_path():
    server, redirect_uri, _q = start_loopback_listener()
    try:
        assert redirect_uri.startswith("http://127.0.0.1:")
        assert redirect_uri.endswith("/callback")
    finally:
        server.server_close()


def test_callback_hit_parses_token_and_is_new():
    server, redirect_uri, q = start_loopback_listener()
    t = _fire_after(0.05, f"{redirect_uri}?token=abc123&isNew=1")
    try:
        result = wait_for_callback(server, q, timeout_s=5)
    finally:
        t.join()
    assert result == {"token": "abc123", "isNew": True}


def test_callback_hit_defaults_is_new_to_false_when_absent():
    server, redirect_uri, q = start_loopback_listener()
    t = _fire_after(0.05, f"{redirect_uri}?token=abc123")
    try:
        result = wait_for_callback(server, q, timeout_s=5)
    finally:
        t.join()
    assert result == {"token": "abc123", "isNew": False}


def test_success_response_body_shows_close_window_message():
    """수신 시 응답 HTML에 "로그인 완료 — 이 창은 닫아도 됩니다"가 실제로 담기는지 확인."""
    server, redirect_uri, q = start_loopback_listener()

    captured = {}

    def _go():
        time.sleep(0.05)
        with urllib.request.urlopen(f"{redirect_uri}?token=abc", timeout=5) as resp:
            captured["body"] = resp.read().decode("utf-8")

    t = threading.Thread(target=_go)
    t.start()
    try:
        wait_for_callback(server, q, timeout_s=5)
    finally:
        t.join()
    assert "로그인 완료 — 이 창은 닫아도 됩니다" in captured["body"]


def test_callback_error_param_raises_login_callback_error():
    server, redirect_uri, q = start_loopback_listener()
    t = _fire_after(0.05, f"{redirect_uri}?error=access_denied")
    try:
        with pytest.raises(LoginCallbackError) as exc_info:
            wait_for_callback(server, q, timeout_s=5)
    finally:
        t.join()
    assert exc_info.value.error == "access_denied"


def test_listener_is_single_shot_after_callback():
    """콜백을 한 번 받으면 리스너가 닫혀 같은 포트로 더 이상 연결할 수 없다."""
    server, redirect_uri, q = start_loopback_listener()
    t = _fire_after(0.05, f"{redirect_uri}?token=abc")
    try:
        wait_for_callback(server, q, timeout_s=5)
    finally:
        t.join()

    with pytest.raises(urllib.error.URLError):
        urllib.request.urlopen(f"{redirect_uri}?token=zzz", timeout=1)


def test_wait_for_callback_times_out_when_nothing_arrives():
    server, _redirect_uri, q = start_loopback_listener()
    started = time.monotonic()
    with pytest.raises(LoginTimeoutError):
        wait_for_callback(server, q, timeout_s=0.3)
    elapsed = time.monotonic() - started
    assert elapsed < 3.0  # 타임아웃이 실제로 짧게 끝나는지(블록되지 않는지) 확인


def test_noise_request_is_ignored_until_real_callback_arrives():
    """/callback 이 아닌 요청(예: favicon.ico)은 무시하고 계속 대기하다 실제 콜백을 받는다."""
    server, redirect_uri, q = start_loopback_listener()

    def _go():
        time.sleep(0.05)
        try:
            urllib.request.urlopen(redirect_uri.rsplit("/callback", 1)[0] + "/favicon.ico", timeout=5)
        except urllib.error.HTTPError:
            pass  # 404 — 의도된 응답
        time.sleep(0.05)
        urllib.request.urlopen(f"{redirect_uri}?token=real-token", timeout=5)

    t = threading.Thread(target=_go)
    t.start()
    try:
        result = wait_for_callback(server, q, timeout_s=5)
    finally:
        t.join()
    assert result == {"token": "real-token", "isNew": False}


def test_run_login_flow_orchestrates_listener_browser_and_backend_fakes():
    """build_authorization_url/open_browser를 가짜로 주입 — 실제 백엔드·브라우저 없이
    전체 오케스트레이션(리스너 오픈 → URL 빌드 → 브라우저 오픈 호출 → 콜백 대기)을 검증."""
    captured = {}

    def fake_build(redirect_uri):
        captured["redirect_uri"] = redirect_uri
        return f"https://accounts.google.com/fake-auth?redirect_uri={redirect_uri}"

    def fake_open_browser(url):
        captured["opened_url"] = url
        # 실제 브라우저 대신 — Google 로그인 완료 후 최종 리다이렉트가 루프백에 도착하는
        # 상황을 흉내낸다.
        _fire_after(0.05, f"{captured['redirect_uri']}?token=tok-xyz&isNew=0")

    result = run_login_flow(fake_build, timeout_s=5, open_browser=fake_open_browser)

    assert result == {"token": "tok-xyz", "isNew": False}
    assert captured["redirect_uri"].startswith("http://127.0.0.1:")
    assert captured["redirect_uri"].endswith("/callback")
    assert captured["opened_url"].startswith("https://accounts.google.com/fake-auth")


def test_run_login_flow_propagates_timeout_when_browser_never_completes():
    def fake_build(redirect_uri):
        return "https://accounts.google.com/fake-auth"

    def fake_open_browser(url):
        pass  # 사용자가 브라우저를 그냥 안 닫고 방치 — 콜백이 영영 안 온다

    with pytest.raises(LoginTimeoutError):
        run_login_flow(fake_build, timeout_s=0.3, open_browser=fake_open_browser)
