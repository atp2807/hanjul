"""메타 테스트 — 마이그레이션이 만드는 스키마와 통합테스트 schema_translate_map 대조.

마이그레이션에 새 스키마(``CREATE SCHEMA IF NOT EXISTS xxx``)를 추가하고
``tests/integration/conftest.py``의 ``schema_translate_map`` 갱신을 잊으면, sqlite
통합테스트가 그 스키마의 테이블을 조용히 인식 못 해 엉뚱한 실패(또는 거짓 통과)로
이어질 수 있다. 여기서 두 목록을 정적으로 대조해 누락을 즉시 잡는다.
"""
import re
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
MIGRATIONS_DIR = BACKEND_DIR / "migrations" / "versions"
CONFTEST_PATH = BACKEND_DIR / "tests" / "integration" / "conftest.py"

CREATE_SCHEMA_RE = re.compile(r"CREATE SCHEMA IF NOT EXISTS (\w+)")
SCHEMA_TRANSLATE_MAP_RE = re.compile(r'"schema_translate_map":\s*\{([^}]*)\}')
MAP_KEY_RE = re.compile(r'"(\w+)":\s*None')


def _schemas_created_by_migrations() -> set[str]:
    schemas: set[str] = set()
    for path in sorted(MIGRATIONS_DIR.glob("*.py")):
        text = path.read_text(encoding="utf-8")
        schemas.update(CREATE_SCHEMA_RE.findall(text))
    return schemas


def _schemas_in_translate_map() -> set[str]:
    text = CONFTEST_PATH.read_text(encoding="utf-8")
    match = SCHEMA_TRANSLATE_MAP_RE.search(text)
    assert match, (
        f"{CONFTEST_PATH} 에서 schema_translate_map 딕셔너리를 찾지 못함 — "
        "정규식(SCHEMA_TRANSLATE_MAP_RE)이 실제 형식과 어긋났을 수 있음"
    )
    return set(MAP_KEY_RE.findall(match.group(1)))


def test_migration_schemas_match_integration_schema_translate_map():
    migration_schemas = _schemas_created_by_migrations()
    mapped_schemas = _schemas_in_translate_map()

    missing_from_conftest = migration_schemas - mapped_schemas
    stale_in_conftest = mapped_schemas - migration_schemas

    assert not missing_from_conftest, (
        f"마이그레이션이 만드는 스키마 {sorted(missing_from_conftest)} 가 "
        f"{CONFTEST_PATH} 의 schema_translate_map 에 없음 — "
        "새 스키마 추가 시 함께 갱신 필요 (CLAUDE.md 컨벤션: "
        "'통합테스트 추가 시 sqlite schema_translate_map 에 새 스키마 추가')"
    )
    assert not stale_in_conftest, (
        f"{CONFTEST_PATH} 의 schema_translate_map 에 있는 스키마 {sorted(stale_in_conftest)} 가 "
        "어떤 마이그레이션에서도 CREATE SCHEMA 되지 않음 — 오탈자이거나 죽은 항목 정리 필요"
    )
