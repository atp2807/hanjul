"""메타 테스트 — OpenAPI 스키마 스냅샷 회귀가드.

라우터/스키마가 의도치 않게 바뀌면(엔드포인트 추가/삭제, 필드명 변경 등) 프론트가
모르는 새 API 계약 변경이 생길 수 있다. ``app.openapi()`` 결과를 스냅샷과 비교해
조기에 드러낸다.

⚠️ pydantic 버전 가드: JSON Schema 직렬화 결과가 pydantic 버전 간 미묘하게 달라질 수
있다. 이 레포의 두 venv는 pydantic 버전이 다르다 —
  - ``.venv``   (3.14): pydantic 2.13.x — 단위/통합 테스트 실행용, CI 정본 아님
  - ``.venv312``(3.12): pydantic 2.9.x  — 런타임/마이그레이션/E2E·CI 정본
그래서 스냅샷은 pydantic 2.9(.venv312)에서만 생성·검증하고, 그 외 버전에서는
skip 한다.
"""
import json
from pathlib import Path

import pydantic
import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
SNAPSHOT_PATH = BACKEND_DIR / "tests" / "fixtures" / "openapi_snapshot.json"
UPDATE_CMD = "cd backend && .venv312/bin/python scripts/update_openapi_snapshot.py"

pytestmark = pytest.mark.skipif(
    not pydantic.VERSION.startswith("2.9"),
    reason=(
        f"OpenAPI 스냅샷은 pydantic 2.9(.venv312, CI 정본)에서만 검증 — "
        f"현재 pydantic {pydantic.VERSION} (.venv, 3.14) 에서는 skip"
    ),
)


def test_openapi_schema_matches_snapshot():
    from main import app

    current = json.dumps(app.openapi(), sort_keys=True, indent=2)

    assert SNAPSHOT_PATH.exists(), (
        f"{SNAPSHOT_PATH} 없음 — 최초 생성 필요:\n  {UPDATE_CMD}"
    )

    expected = SNAPSHOT_PATH.read_text(encoding="utf-8")
    assert current == expected, (
        "OpenAPI 스키마가 스냅샷과 다름. 의도된 API 변경(엔드포인트/필드 추가·삭제·변경)이면 "
        f"아래 명령으로 스냅샷을 갱신하고 커밋할 것:\n  {UPDATE_CMD}\n"
        "의도치 않은 변경이면 원인 커밋을 확인할 것."
    )
