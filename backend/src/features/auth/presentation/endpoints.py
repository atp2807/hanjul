"""auth API 엔드포인트 — 소셜 로그인 (브라우저 리다이렉트 플로우 + 데스크탑 루프백 플로우).

데스크탑(한줄 IDE P1 슬라이스5, RFC 8252)은 이 플로우를 시스템 브라우저로 그대로 타되,
콜백 후 최종 리다이렉트 대상만 `next` 쿼리로 지정한다. `next` 미지정 시(기존 웹 프론트)는
동작이 100% 그대로다 — 아래 각 함수 docstring 참고.
"""
import json
import logging
import re
from urllib.parse import urlencode

from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse

from src.config.settings import settings
from src.features.auth.application.auth_service import AuthService
from src.features.auth.domain.models import OAuthExchangeError, SocialProfile
from src.features.auth.presentation.dependencies import get_auth_service
from src.features.auth.presentation.schemas import LoginUrlResponse
from src.shared.errors import NotFoundError, ValidationError

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger("app")

# 데스크탑 루프백 콜백 allowlist(RFC 8252 §7.3) — 127.0.0.1 리터럴 + /callback 경로만 허용.
# localhost 표기는 일부러 불허(일부 OS/네트워크 설정에서 non-loopback으로 리졸브될 수 있어
# RFC가 리터럴 IP를 권고) — 형식 벗어나면 조용히 기본값으로 대체하지 않고 422로 알린다
# (이게 곧 open redirect 방지 — 실패를 숨기지 않는 것 자체가 설계 의도).
_LOOPBACK_NEXT_RE = re.compile(r"^http://127\.0\.0\.1:\d{1,5}/callback$")

# OAuth state에 next를 실어 보낼 때 붙이는 마커. 없으면(next 미지정 로그인) state는 그대로
# opaque 문자열로 왕복한다 — 기존 웹 플로우와 완전히 동일(디코드 시도조차 안 함).
_STATE_NEXT_PREFIX = "dnext:"


def _validate_next(next_url: str) -> None:
    """루프백 콜백 allowlist 검증. 통과 못 하면 ValidationError(422)."""
    if not _LOOPBACK_NEXT_RE.match(next_url):
        raise ValidationError(
            "next는 http://127.0.0.1:<port>/callback 형식만 허용돼요(localhost 표기 불가)."
        )


def _encode_state(client_state: str, next_url: str | None) -> str:
    """next 없으면 client_state 그대로 반환(기존 동작 불변). 있으면 Google 왕복에 실어 보낼
    수 있게 JSON 봉투를 씌운다 — client_state도 함께 보존(현재 미사용, 확장 여지)."""
    if next_url is None:
        return client_state
    return _STATE_NEXT_PREFIX + json.dumps({"s": client_state, "next": next_url})


def _decode_next(state: str) -> str | None:
    """callback에서 state를 되풀어 next를 꺼낸다. 봉투 마커가 없거나 파싱 실패하면
    (next 없이 로그인했거나 예기치 않은 state) None — 기존 웹 플로우로 그대로 폴백한다."""
    if not state.startswith(_STATE_NEXT_PREFIX):
        return None
    try:
        payload = json.loads(state[len(_STATE_NEXT_PREFIX) :])
        next_url = payload.get("next") if isinstance(payload, dict) else None
        return next_url if isinstance(next_url, str) else None
    except json.JSONDecodeError:
        return None


def _redirect(next_url: str | None, **params: str) -> RedirectResponse:
    """next(검증된 루프백)가 있으면 쿼리스트링(`?token=...`)으로, 없으면 기존 프론트
    fragment(`#token=...`)로 리다이렉트. 루프백 리스너는 순수 HTTP 서버라 fragment를 받을
    수 없다(fragment는 브라우저만 해석해 서버로는 애초에 전송되지 않는다 — RFC 8252 §5
    데스크탑 앱 패턴이 쿼리스트링을 쓰는 이유).

    TODO(하드닝): 지금은 토큰을 URL에 직접 싣는다 — 다음 단계로 일회성 코드 교환을 얹으면
    브라우저 히스토리/프록시 로그에 토큰 원문이 남는 노출면을 줄일 수 있다.
    """
    qs = urlencode(params)
    if next_url:
        return RedirectResponse(url=f"{next_url}?{qs}", status_code=302)
    return RedirectResponse(url=f"{settings.FRONTEND_URL}/auth/callback#{qs}", status_code=302)


@router.get("/{provider}/login", response_model=LoginUrlResponse)
async def login(
    provider: str,
    state: str = "",
    next: str | None = None,
    service: AuthService = Depends(get_auth_service),
) -> LoginUrlResponse:
    """소셜 로그인 시작 URL 생성.

    `next`(선택, 데스크탑 전용) = 콜백 후 리다이렉트할 루프백 주소
    (`http://127.0.0.1:<port>/callback`). allowlist를 통과해야만(아니면 422) OAuth
    `state`에 실려 Google 왕복 후 `callback()`에서 되꺼내진다. 미지정 시(웹 플로우) 동작
    불변 — `state`는 그대로 opaque 값으로 통과한다.
    """
    if next is not None:
        _validate_next(next)  # 불허 값은 조용히 기본값으로 대체하지 않는다(open redirect 방지).
    url = service.login_url(provider, _encode_state(state, next))
    return LoginUrlResponse(authorization_url=url)


@router.get("/test-login")
async def test_login(
    email: str,
    name: str = "테스트작가",
    next: str | None = None,
    service: AuthService = Depends(get_auth_service),
) -> RedirectResponse:
    """E2E/로컬 전용 로그인 우회 — Google 콜백과 동일하게 토큰을 전달.

    settings.E2E_LOGIN_ENABLED 가 True 일 때만 동작. 운영 기본값은 차단(404, fail-closed).
    경로는 1세그먼트라 /{provider}/login·/{provider}/callback 과 충돌하지 않는다.

    `next`(선택) — 이 경로는 Google 왕복이 없어 state 봉투가 필요 없다(바로 allowlist만
    검증). 데스크탑 개발 편의용 — 실 Google OAuth 자격증명 없이 로컬에서 루프백 로그인
    플로우를 손으로 확인할 때 쓴다(desktop/README.md 절차 참고).
    """
    if not settings.E2E_LOGIN_ENABLED:
        raise NotFoundError("not found")
    if next is not None:
        _validate_next(next)
    profile = SocialProfile("GOOGLE", f"e2e:{email}", email, name)
    result = await service.login_with_profile(profile)
    return _redirect(next, token=result.token, isNew="1" if result.is_new else "0")


@router.get("/{provider}/callback")
async def callback(
    provider: str,
    code: str | None = None,
    error: str | None = None,
    state: str = "",
    service: AuthService = Depends(get_auth_service),
) -> RedirectResponse:
    """Google 콜백 처리 → JWT 발급 → 리다이렉트.

    토큰은 기본적으로 URL fragment(#)로 전달(서버 로그·Referer 헤더에 안 남는다). `state`에
    루프백 `next`가 실려 있으면(=`/login`에서 실은 값) 대신 그 주소로 `?token=`을 전달한다
    (`_redirect` 참고). 실패(사용자 취소·교환 실패)는 500/422 대신 안내 리다이렉트로 전달.
    """
    next_url = _decode_next(state)
    if next_url is not None:
        try:
            _validate_next(next_url)
        except ValidationError:
            # 이중 검증(state 위조 대비) — /login을 거치지 않고 Google 인가 URL을 직접
            # 조작해(예: client_id만 알면 누구나 authorization_url 생성 가능) 위조 state로
            # 여기 도달했을 가능성을 방어한다. 토큰을 위조 next로 흘려보내지 않기 위해
            # 조용히 기본 웹 플로우로 폴백한다 — 사용자는 이미 정상적으로 Google 로그인을
            # 마쳤으므로, 에러를 보여주는 대신 평소처럼 프론트로 보내는 편이 안전하다.
            logger.warning("auth callback: state 안의 next 재검증 실패 — 기본 플로우로 폴백")
            next_url = None

    if error or not code:
        # 사용자가 동의 취소(access_denied) 또는 code 없음 → 422 대신 안내 리다이렉트
        return _redirect(next_url, error=error or "no_code")
    try:
        result = await service.complete_login(provider, code)
    except OAuthExchangeError as e:
        # OAuth 교환 실패는 HTTP 에러가 아니라 안내 리다이렉트(#error=/?error=)로 변환.
        logger.warning("OAuth 교환 실패 provider=%s: %s", provider, e.detail)  # redirect_uri_mismatch 등
        return _redirect(next_url, error="auth_failed")
    # UnknownProvider 400 은 도메인 예외 → 중앙 핸들러가 매핑.
    return _redirect(next_url, token=result.token, isNew="1" if result.is_new else "0")
