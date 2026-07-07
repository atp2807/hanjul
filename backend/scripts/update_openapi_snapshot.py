"""OpenAPI 스키마 스냅샷 갱신 — tests/meta/test_openapi_snapshot.py 회귀가드용.

⚠️ 반드시 .venv312(3.12, pydantic 2.9.x — 런타임/CI 정본)로 실행할 것.
   .venv(3.14, pydantic 2.13.x)로 실행하면 JSON Schema 직렬화가 미묘하게 달라져
   CI(.venv312)에서 다시 스냅샷 불일치로 실패하는 결과물을 만들게 된다.
   이 스크립트는 시작 시 pydantic 버전을 확인하고, 2.9 계열이 아니면 즉시 중단한다.

사용: backend 디렉토리에서
    .venv312/bin/python scripts/update_openapi_snapshot.py

의도된 API 변경(엔드포인트/스키마 필드 추가·삭제·변경) 후에만 실행할 것 — 그 외의
스냅샷 불일치는 의도치 않은 계약 변경을 잡아낸 것이니 원인을 먼저 확인.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pydantic  # noqa: E402

if not pydantic.VERSION.startswith("2.9"):
    sys.exit(
        f"pydantic {pydantic.VERSION} 감지 — .venv312(pydantic 2.9.x)로 실행해야 함.\n"
        "  cd backend && .venv312/bin/python scripts/update_openapi_snapshot.py"
    )

from main import app  # noqa: E402

SNAPSHOT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "tests",
    "fixtures",
    "openapi_snapshot.json",
)


def main() -> int:
    snapshot = json.dumps(app.openapi(), sort_keys=True, indent=2)
    with open(SNAPSHOT_PATH, "w", encoding="utf-8") as f:
        f.write(snapshot)
    print(f"OpenAPI 스냅샷 갱신 완료 → {SNAPSHOT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
