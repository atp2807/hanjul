"""desktop/token_store.py(P1 슬라이스5, OS 키체인 토큰 보관) 단위 테스트.

실 OS 키체인은 절대 건드리지 않는다 — ``keyring.get_password``/``set_password``/
``delete_password`` 를 인메모리 dict 기반 가짜로 monkeypatch 해서, 우리 wrapper의 로직
(조회/저장/삭제 위임 + 에러를 KeyringUnavailableError로 정규화)만 검증한다.
"""

import keyring.errors
import pytest

import token_store


class _FakeKeyring:
    """서비스/유저명 하나짜리 인메모리 keyring 대역."""

    def __init__(self):
        self._store: dict[tuple[str, str], str] = {}

    def get_password(self, service, username):
        return self._store.get((service, username))

    def set_password(self, service, username, password):
        self._store[(service, username)] = password

    def delete_password(self, service, username):
        try:
            del self._store[(service, username)]
        except KeyError:
            raise keyring.errors.PasswordDeleteError("not found") from None


class _BrokenKeyring:
    """백엔드 자체가 없는 환경(예: headless Linux) 흉내 — 모든 호출이 KeyringError."""

    def get_password(self, service, username):
        raise keyring.errors.NoKeyringError("no backend")

    def set_password(self, service, username, password):
        raise keyring.errors.NoKeyringError("no backend")

    def delete_password(self, service, username):
        raise keyring.errors.NoKeyringError("no backend")


@pytest.fixture
def fake_keyring(monkeypatch):
    fake = _FakeKeyring()
    monkeypatch.setattr(token_store.keyring, "get_password", fake.get_password)
    monkeypatch.setattr(token_store.keyring, "set_password", fake.set_password)
    monkeypatch.setattr(token_store.keyring, "delete_password", fake.delete_password)
    return fake


@pytest.fixture
def broken_keyring(monkeypatch):
    broken = _BrokenKeyring()
    monkeypatch.setattr(token_store.keyring, "get_password", broken.get_password)
    monkeypatch.setattr(token_store.keyring, "set_password", broken.set_password)
    monkeypatch.setattr(token_store.keyring, "delete_password", broken.delete_password)
    return broken


def test_get_token_defaults_to_none(fake_keyring):
    assert token_store.get_token() is None


def test_set_then_get_token_round_trips(fake_keyring):
    token_store.set_token("tok-abc123")
    assert token_store.get_token() == "tok-abc123"


def test_set_token_overwrites_previous(fake_keyring):
    token_store.set_token("first")
    token_store.set_token("second")
    assert token_store.get_token() == "second"


def test_delete_token_removes_stored_value(fake_keyring):
    token_store.set_token("tok-abc123")
    token_store.delete_token()
    assert token_store.get_token() is None


def test_delete_token_is_idempotent_when_nothing_stored(fake_keyring):
    """로그아웃 — 애초에 로그인한 적 없어도 에러가 나면 안 된다."""
    token_store.delete_token()  # 에러 없이 조용히 통과해야 함
    assert token_store.get_token() is None


def test_get_token_raises_clear_error_when_backend_unavailable(broken_keyring):
    with pytest.raises(token_store.KeyringUnavailableError):
        token_store.get_token()


def test_set_token_raises_clear_error_when_backend_unavailable(broken_keyring):
    """실 로그인 저장 실패는 조용한 평문 폴백이 아니라 명시적 에러여야 한다(설계결정 4)."""
    with pytest.raises(token_store.KeyringUnavailableError):
        token_store.set_token("tok-abc123")


def test_delete_token_raises_clear_error_when_backend_unavailable(broken_keyring):
    with pytest.raises(token_store.KeyringUnavailableError):
        token_store.delete_token()
