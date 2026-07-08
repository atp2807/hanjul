"""소셜 콜백(302 리다이렉트) 테스트 헬퍼.

콜백이 더 이상 JSON을 반환하지 않고 프론트로 리다이렉트하므로,
Location fragment(#token=...&isNew=...)에서 토큰을 추출한다.
"""
import uuid
from urllib.parse import parse_qs

from src.features.auth.presentation.dependencies import token_issuer


async def login_token(client, provider: str, code: str) -> tuple[str, bool]:
    """콜백 → 302. Location fragment 에서 (token, is_new) 추출."""
    r = await client.get(f"/api/auth/{provider}/callback?code={code}", follow_redirects=False)
    assert r.status_code == 302, r.text
    fragment = r.headers["location"].split("#", 1)[1]
    params = parse_qs(fragment)
    return params["token"][0], params.get("isNew", ["0"])[0] == "1"


async def login_account(client, provider: str, code: str) -> tuple[str, dict]:
    """로그인 후 /me 로 계정 정보까지 → (token, account_dict). (get_session 오버라이드 필요)

    ⚠️ `code`는 계정 구분자가 아니다 — conftest의 FakeProvider는 실제 OAuth와 마찬가지로
    (같은 사람이 재로그인해도 code는 매번 다르다는 걸 모사해) code 값과 무관하게 고정된
    `social_profile` fixture 하나만 돌려준다. 즉 이 함수를 code만 바꿔 여러 번 불러도
    **전부 같은 계정**이다(2026-07-08 실제로 이 착각으로 만든 회귀테스트가 아무것도
    검증 못 하고 통과한 사례 — lr-747a0b49). 한 테스트 함수 안에서 진짜 서로 다른 계정이
    필요하면 이 함수 대신 `fresh_account_auth()`를 쓸 것.
    """
    token, _ = await login_token(client, provider, code)
    me = await client.get("/api/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200, f"/me {me.status_code}: {me.text}"
    return token, me.json()


def fresh_account_auth(role: str = "READER") -> dict:
    """OAuth 콜백 왕복 없이 새 UUID로 토큰을 직접 발급 — 한 테스트 함수 안에서 서로 다른
    계정이 여러 개 필요할 때 쓴다(예: 작가 vs 제3자 vs 구매자 접근제어 테스트).

    login_account()와 달리 code 인자가 없다 — 매 호출이 항상 새 계정이라 헷갈릴 여지가
    없다. SQLite 테스트 DB는 FK를 강제하지 않아 accounts 테이블에 실제 행이 없어도
    인증은 통과한다(토큰의 sub=UUID만 검증). 반환값은 그대로 httpx 헤더로 쓸 수 있는 dict.
    """
    token = token_issuer().issue(uuid.uuid4(), role)
    return {"Authorization": f"Bearer {token}"}
