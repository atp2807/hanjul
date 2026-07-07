"""한줄 IDE 데스크탑 — 로그인 토큰 보관(OS 키체인). P1 슬라이스5.

`keyring` 패키지 위에 macOS Keychain/Windows Credential Locker로 저장한다. 실 로그인
(``auth_flow.run_login_flow`` → ``app.py`` ``Api.login()``)의 정본 저장소는 여기다 — 기존
평문 ``setting.token``(desktop/store.py)은 dev 수동 토큰 입력 전용 폴백으로만 남는다
(``app.py`` 의 ``_effective_token`` 이 keyring 우선 · 평문 폴백 순서로 조회).

설계결정(스펙 4): keyring 백엔드 자체가 없거나 접근 실패하는 환경에서는 조용히 평문으로
대체하지 않고 ``KeyringUnavailableError`` 를 명시적으로 던진다 — "실 로그인이 조용히
평문 저장으로 격하되는" 상황을 막기 위함. dev 수동 입력(``store.save_settings``)은 이
모듈을 거치지 않는 별개 경로라 keyring 부재와 무관하게 항상 동작한다.
"""

import keyring
import keyring.errors

# 단일 로컬 사용자 앱 — 계정별로 나눌 필요 없이 토큰 하나만 이 (service, username) 아래 보관.
_SERVICE = "hanjul-ide"
_USERNAME = "token"


class KeyringUnavailableError(Exception):
    """OS 키체인 접근 실패 — 조용한 평문 폴백 대신 호출자에게 명시적으로 알린다."""


def get_token() -> str | None:
    """저장된 토큰(없으면 None). 키체인 백엔드 자체를 못 쓰는 환경은 예외."""
    try:
        return keyring.get_password(_SERVICE, _USERNAME)
    except keyring.errors.KeyringError as exc:
        raise KeyringUnavailableError(f"OS 키체인을 사용할 수 없어요: {exc}") from exc


def set_token(token: str) -> None:
    """로그인 성공 후 토큰 저장. 실패는 그대로 전파(호출자가 "로그인 실패"로 받는다)."""
    try:
        keyring.set_password(_SERVICE, _USERNAME, token)
    except keyring.errors.KeyringError as exc:
        raise KeyringUnavailableError(f"OS 키체인을 사용할 수 없어요: {exc}") from exc


def delete_token() -> None:
    """로그아웃 — 저장된 적 없어도 에러 아님(멱등)."""
    try:
        keyring.delete_password(_SERVICE, _USERNAME)
    except keyring.errors.PasswordDeleteError:
        pass  # 애초에 없었음 — 로그아웃 관점에서는 목표 상태 이미 달성.
    except keyring.errors.KeyringError as exc:
        raise KeyringUnavailableError(f"OS 키체인을 사용할 수 없어요: {exc}") from exc
