"""desktop/scripts/publish_live.py — 로컬 dev 백엔드에 실제로 발행해보는 수동 검증 스크립트.

opt-in: RUN_PUBLISH_LIVE=1 일 때만 동작(네트워크 + 실행 중인 백엔드 필요) — 평소엔
안내만 출력하고 종료한다. `backend/tests/integration/test_toss_live.py`의 env-gate
관례를 그대로 따르되, 이건 pytest 테스트가 아니라 독립 스크립트다 — desktop pytest 는
`.venv`(3.14, aiosqlite)로 실행되고 실 백엔드는 `.venv312`(3.12, asyncpg) 별도 프로세스로
뜨기 때문에, 여기서는 그 실 백엔드를 순수 HTTP로만 두드린다(테스트 스위트에 넣지 않음).

준비:
    cd backend && .venv312/bin/alembic upgrade head   # 최초 1회, DB 마이그레이션
    cd backend && E2E_LOGIN_ENABLED=1 .venv312/bin/uvicorn main:app \\
        --host 127.0.0.1 --port 28000

실행:
    cd desktop && RUN_PUBLISH_LIVE=1 .venv/bin/python scripts/publish_live.py

무엇을 확인하나: (사용자의 실제 desktop/data/ide.db는 절대 건드리지 않고) 임시 SQLite에
책 1권 + 문단 있는 챕터 1개를 만들어 `POST /books` → `PUT content` → `POST publish-now`
까지 실 서버로 왕복시키고 최종 결과(JSON)를 출력한다. 토큰은
`GET /api/auth/test-login`(E2E_LOGIN_ENABLED 전용 우회,
backend/src/features/auth/presentation/endpoints.py:31-44)의 302 리다이렉트
Location 헤더 fragment(`#token=...`)에서 직접 뽑는다 — 리다이렉트를 실제로 따라가면
fragment 를 든 채 프론트 URL로 GET 해버려 값을 잃으므로, 리다이렉트 자체를 따라가지
않는 opener 를 쓴다.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import parse_qs, quote, urlsplit

_DESKTOP_DIR = Path(__file__).resolve().parent.parent
if str(_DESKTOP_DIR) not in sys.path:
    sys.path.insert(0, str(_DESKTOP_DIR))

from publisher import publish  # noqa: E402
from store import Store  # noqa: E402

DEFAULT_API_BASE = os.environ.get("HANJUL_API_BASE", "http://127.0.0.1:28000")
TEST_LOGIN_EMAIL = os.environ.get("HANJUL_TEST_LOGIN_EMAIL", "publish-live@example.com")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """redirect_request가 None을 반환하면 urllib은 그 302를 그냥 HTTPError로 올린다
    (실측 확인됨) — `exc.headers`에서 Location을 그대로 읽을 수 있다. 따라가면 fragment
    (`#token=...`)를 든 채 프론트 URL로 GET해버려 토큰을 잃는다."""

    def redirect_request(self, *args, **kwargs):
        return None


def _fetch_test_login_token(api_base: str, email: str) -> str:
    opener = urllib.request.build_opener(_NoRedirect)
    url = f"{api_base}/api/auth/test-login?email={quote(email)}"
    try:
        opener.open(url)
    except urllib.error.HTTPError as exc:
        if exc.code != 302:
            raise RuntimeError(
                f"test-login 실패: HTTP {exc.code} — E2E_LOGIN_ENABLED=1 로 백엔드를 "
                "띄웠는지 확인하세요(꺼져 있으면 404)."
            ) from None
        location = exc.headers.get("Location")
    else:
        raise RuntimeError("test-login이 302가 아닌 정상 응답을 줌 — 예상 밖 상태")

    if not location:
        raise RuntimeError("test-login 302 응답에 Location 헤더가 없음")
    fragment = urlsplit(location).fragment  # "token=...&isNew=..."
    token = parse_qs(fragment).get("token", [None])[0]
    if not token:
        raise RuntimeError(f"Location에서 token을 못 찾음: {location!r}")
    return token


def main() -> int:
    if not os.environ.get("RUN_PUBLISH_LIVE"):
        print(
            "RUN_PUBLISH_LIVE=1 일 때만 동작합니다(네트워크 + 실행 중인 로컬 백엔드 필요).\n"
            "준비: cd backend && E2E_LOGIN_ENABLED=1 .venv312/bin/uvicorn main:app "
            "--host 127.0.0.1 --port 28000\n"
            "실행: cd desktop && RUN_PUBLISH_LIVE=1 .venv/bin/python scripts/publish_live.py"
        )
        return 0

    api_base = DEFAULT_API_BASE
    print(f"[1/3] test-login 토큰 발급 중... ({api_base}, email={TEST_LOGIN_EMAIL})")
    try:
        token = _fetch_test_login_token(api_base, TEST_LOGIN_EMAIL)
    except (urllib.error.URLError, RuntimeError) as exc:
        print(f"실패: {exc}")
        return 1
    print(f"    토큰 확보 (길이 {len(token)})")

    with tempfile.TemporaryDirectory(prefix="hanjul_publish_live_") as tmp_dir:
        db_path = Path(tmp_dir) / "ide.db"
        store = Store(db_path)  # 사용자의 실제 desktop/data/ide.db 와 무관한 임시 DB
        chapter_id = store.list_chapters()[0]["id"]
        store.save_chapter(
            chapter_id,
            {
                "html": (
                    '<article data-juldoc="1">'
                    "<p>publish_live.py 가 만든 검증용 문단입니다.</p>"
                    "</article>"
                )
            },
        )

        print("[2/3] 발행 중 (프리플라이트 → book 생성 → content 교체 → publish-now)...")
        result = publish(store, {"apiBase": api_base, "token": token})

    print("[3/3] 결과:")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result.get("ok") and result.get("error", {}).get("status") == 422:
        print(
            "\n참고: 422 + '가격을 먼저 설정' 류 메시지면 정상적인 실패입니다 — 이 "
            "슬라이스는 가격 설정 UI가 없어서(publisher.py 모듈 docstring \"미해결\" "
            "참고) 새로 만든 책은 가격 없이 즉시출판을 시도하게 됩니다. 웹 스튜디오에서 "
            "해당 책 가격을 설정한 뒤 다시 실행하면 통과합니다."
        )
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
