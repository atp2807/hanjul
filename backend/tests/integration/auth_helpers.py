"""소셜 콜백(302 리다이렉트) 테스트 헬퍼.

콜백이 더 이상 JSON을 반환하지 않고 프론트로 리다이렉트하므로,
Location fragment(#token=...&isNew=...)에서 토큰을 추출한다.
"""
from urllib.parse import parse_qs


async def login_token(client, provider: str, code: str) -> tuple[str, bool]:
    """콜백 → 302. Location fragment 에서 (token, is_new) 추출."""
    r = await client.get(f"/api/auth/{provider}/callback?code={code}", follow_redirects=False)
    assert r.status_code == 302, r.text
    fragment = r.headers["location"].split("#", 1)[1]
    params = parse_qs(fragment)
    return params["token"][0], params.get("isNew", ["0"])[0] == "1"


async def login_account(client, provider: str, code: str) -> tuple[str, dict]:
    """로그인 후 /me 로 계정 정보까지 → (token, account_dict). (get_session 오버라이드 필요)"""
    token, _ = await login_token(client, provider, code)
    me = await client.get("/api/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200, f"/me {me.status_code}: {me.text}"
    return token, me.json()
