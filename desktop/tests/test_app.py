"""desktop/app.py 의 Api.login/logout/whoami + 토큰 소스 우선순위(P1 슬라이스5) 단위 테스트.

실 브라우저·실 백엔드·실 OS 키체인은 전혀 쓰지 않는다 — `app` 모듈에 이미 바인딩된
`_request`/`run_login_flow`/`get_token`/`set_token`/`delete_token` 이름을 monkeypatch 해서
Api 메서드의 오케스트레이션(무엇을 어떤 인자로 호출하고 결과를 어떻게 조합하는지)만
검증한다. 리스너 자체는 test_auth_flow.py, keyring wrapper 자체는 test_token_store.py 담당.
"""

import pytest

import app
from store import Store


@pytest.fixture
def store(tmp_path):
    return Store(tmp_path / "ide.db")


@pytest.fixture
def api(store):
    return app.Api(store)


# ── login() ──────────────────────────────────────────────────────────────


def test_login_builds_authorization_url_with_loopback_next_and_stores_via_keyring(
    monkeypatch, store, api
):
    store.save_settings({"apiBase": "http://127.0.0.1:28000"})

    captured_requests = []

    def fake_request(settings, method, path):
        captured_requests.append((settings, method, path))
        if path.startswith("/auth/google/login"):
            return 200, {"authorizationUrl": "https://accounts.google.com/fake-auth"}
        if path == "/me":
            return 200, {
                "id": "u1",
                "email": "me@example.com",
                "displayName": "나",
                "role": "READER",
            }
        raise AssertionError(f"unexpected path: {path}")  # pragma: no cover

    def fake_run_login_flow(build_authorization_url, timeout_s=120):
        # login()이 넘긴 콜백을 실제로 호출해 next= 인코딩까지 함께 검증한다.
        url = build_authorization_url("http://127.0.0.1:54321/callback")
        assert url == "https://accounts.google.com/fake-auth"
        return {"token": "tok-abc", "isNew": False}

    stored = {}
    monkeypatch.setattr(app, "_request", fake_request)
    monkeypatch.setattr(app, "run_login_flow", fake_run_login_flow)
    monkeypatch.setattr(app, "set_token", lambda t: stored.update(token=t))
    monkeypatch.setattr(app, "get_token", lambda: stored.get("token"))

    result = api.login()

    assert stored["token"] == "tok-abc"
    assert result == {
        "id": "u1",
        "email": "me@example.com",
        "displayName": "나",
        "role": "READER",
    }
    login_call = next(c for c in captured_requests if c[2].startswith("/auth/google/login"))
    # 루프백 redirect_uri가 URL-인코딩되어 next= 쿼리에 실렸는지(콜론·슬래시 인코딩 확인)
    assert "next=http%3A%2F%2F127.0.0.1%3A54321%2Fcallback" in login_call[2]


def test_login_defaults_api_base_when_unset(monkeypatch, store, api):
    """apiBase를 한 번도 설정한 적 없어도(최초 실행) 기본값(_DEFAULT_API_BASE)으로 시도한다."""
    captured = {}

    def fake_request(settings, method, path):
        captured["api_base"] = settings["apiBase"]
        if path.startswith("/auth/google/login"):
            return 200, {"authorizationUrl": "https://x"}
        return 200, {"id": "u", "email": "e", "displayName": "d", "role": "READER"}

    def fake_run_login_flow(build_authorization_url, timeout_s=120):
        build_authorization_url("http://127.0.0.1:1/callback")  # login()이 안전하게 넘기는지만 확인
        return {"token": "t", "isNew": True}

    stored = {}
    monkeypatch.setattr(app, "_request", fake_request)
    monkeypatch.setattr(app, "run_login_flow", fake_run_login_flow)
    monkeypatch.setattr(app, "set_token", lambda t: stored.update(token=t))
    monkeypatch.setattr(app, "get_token", lambda: stored.get("token"))

    result = api.login()

    assert captured["api_base"] == app._DEFAULT_API_BASE
    assert result["email"] == "e"


def test_login_propagates_keyring_unavailable_from_set_token(monkeypatch, store, api):
    """keyring 저장 실패는 조용히 평문으로 대체하지 않고 그대로 전파한다(설계결정 4)."""
    monkeypatch.setattr(
        app, "_request", lambda settings, method, path: (200, {"authorizationUrl": "https://x"})
    )
    monkeypatch.setattr(
        app, "run_login_flow", lambda build, timeout_s=120: {"token": "tok", "isNew": False}
    )

    def boom(token):
        raise app.KeyringUnavailableError("no backend")

    monkeypatch.setattr(app, "set_token", boom)

    with pytest.raises(app.KeyringUnavailableError):
        api.login()


def test_login_propagates_timeout_from_flow(monkeypatch, store, api):
    from auth_flow import LoginTimeoutError

    monkeypatch.setattr(
        app, "_request", lambda settings, method, path: (200, {"authorizationUrl": "https://x"})
    )

    def fake_run_login_flow(build, timeout_s=120):
        build("http://127.0.0.1:1/callback")
        raise LoginTimeoutError("timed out")

    monkeypatch.setattr(app, "run_login_flow", fake_run_login_flow)

    with pytest.raises(LoginTimeoutError):
        api.login()


# ── logout() ─────────────────────────────────────────────────────────────


def test_logout_deletes_keyring_token_and_is_idempotent(monkeypatch, api):
    calls = []
    monkeypatch.setattr(app, "delete_token", lambda: calls.append(1))

    result = api.logout()

    assert result == {"ok": True}
    assert calls == [1]


# ── whoami() ─────────────────────────────────────────────────────────────


def test_whoami_returns_none_without_any_token(monkeypatch, api):
    monkeypatch.setattr(app, "get_token", lambda: None)
    assert api.whoami() is None


def test_whoami_calls_me_endpoint_with_effective_token(monkeypatch, store, api):
    store.save_settings({"apiBase": "http://127.0.0.1:28000"})
    monkeypatch.setattr(app, "get_token", lambda: "keyring-tok")

    captured = {}

    def fake_request(settings, method, path):
        captured.update(settings=settings, method=method, path=path)
        return 200, {"id": "u1", "email": "me@example.com", "displayName": "나", "role": "READER"}

    monkeypatch.setattr(app, "_request", fake_request)

    result = api.whoami()

    assert result["email"] == "me@example.com"
    assert captured["path"] == "/me"
    assert captured["settings"]["token"] == "keyring-tok"


def test_whoami_returns_none_on_401(monkeypatch, store, api):
    store.save_settings({"apiBase": "http://127.0.0.1:28000", "token": "stale"})
    monkeypatch.setattr(app, "get_token", lambda: None)  # keyring 비어있음 → 평문 폴백 사용

    def fake_request(settings, method, path):
        raise app.PublishHttpError(401, "unauthorized")

    monkeypatch.setattr(app, "_request", fake_request)

    assert api.whoami() is None


def test_whoami_reraises_non_401_http_errors(monkeypatch, store, api):
    """서버 다운/5xx 등은 "로그인 안 됨"으로 감추지 않고 그대로 올린다."""
    store.save_settings({"apiBase": "http://127.0.0.1:1", "token": "tok"})
    monkeypatch.setattr(app, "get_token", lambda: None)

    def fake_request(settings, method, path):
        raise app.PublishHttpError(None, "connection refused")

    monkeypatch.setattr(app, "_request", fake_request)

    with pytest.raises(app.PublishHttpError):
        api.whoami()


# ── 토큰 소스 우선순위(keyring 우선 · 평문 폴백) ──────────────────────────


def test_get_settings_prefers_keyring_token_over_plaintext(monkeypatch, store, api):
    store.save_settings({"token": "plaintext-tok-1234"})
    monkeypatch.setattr(app, "get_token", lambda: "keyring-tok-5678")

    settings = api.get_settings()

    assert settings["hasToken"] is True
    assert settings["token"].endswith("5678")


def test_get_settings_falls_back_to_plaintext_when_keyring_empty(monkeypatch, store, api):
    store.save_settings({"token": "plaintext-tok-1234"})
    monkeypatch.setattr(app, "get_token", lambda: None)

    settings = api.get_settings()

    assert settings["token"].endswith("1234")


def test_get_settings_falls_back_to_plaintext_when_keyring_unavailable(monkeypatch, store, api):
    """keyring 백엔드 자체가 없는 환경(headless 등)에서도 dev 수동 입력 폴백은 계속 동작해야 한다."""
    store.save_settings({"token": "plaintext-tok-1234"})

    def boom():
        raise app.KeyringUnavailableError("no backend")

    monkeypatch.setattr(app, "get_token", boom)

    settings = api.get_settings()

    assert settings["token"].endswith("1234")


def test_publish_uses_effective_token(monkeypatch, store, api):
    store.save_settings({"apiBase": "http://127.0.0.1:28000"})
    monkeypatch.setattr(app, "get_token", lambda: "keyring-tok")

    captured = {}

    def fake_publish_book(store_arg, settings):
        captured["settings"] = settings
        return {"ok": True, "remoteBookId": "b1", "chapterCount": 1}

    monkeypatch.setattr(app, "publish_book", fake_publish_book)

    result = api.publish()

    assert result["ok"] is True
    assert captured["settings"]["token"] == "keyring-tok"
