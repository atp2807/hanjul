#!/usr/bin/env python3
"""네이밍 린터 — 응답에 새는 DB 접미어(_cd·_yn·_ts·_dt)를 CI에서 차단.

정책 출처: 공용 네이밍 사전 ``naming_dic/dictionary.json``.
- 규칙 ``db_column_suffix``: DB 컬럼은 접미어(_cd·_ts·_amt·_yn·_no…)를 붙인다.
- 필드 ``status_cd``: "ORM에서는 status로 매핑" — 코드 접미어는 속성/API에서 벗긴다.
- 규칙 ``amount_suffix``: 금액은 _amt 를 API에서도 유지(예외 없음).

CI 자체완결(별도 레포 naming_dic 미체크아웃)을 위해 정책을 여기 vendored.
naming_dic 갱신 시 아래 FORBIDDEN 동기화.

규칙: SQLAlchemy 모델 속성명 · Pydantic 스키마 필드명 · 도메인 View 필드명이
_cd·_yn·_ts·_dt 로 끝나면 위반(→ status·is_read·created_at 등 친화명).
  · DB 컬럼명은 Column("status_cd", …) 문자열이라 검사 대상 아님 — 접미어 OK.
  · 금액(_amt)·번호(_no)·수량(_cnt)·암호화(_enc) 등은 API에서 유지 → 허용.
"""
import ast
import sys
from pathlib import Path

# 속성/필드명에서 금지하는 "DB 전용" 접미어 (→ 친화명/is_/_at 로).
FORBIDDEN = ("_cd", "_yn", "_ts", "_dt")

# 예외 — 순수 내부(응답 미노출) + rename이 지역변수와 얽혀 위험한 것. 신규 추가 지양.
#   provider_cd: OAuth 제공자 코드. auth_service의 지역 provider 변수와 충돌.
ALLOWLIST = {"provider_cd"}

SRC = Path(__file__).resolve().parent.parent / "src"
SCAN_DIRS = [SRC / "infrastructure" / "db" / "models"]
SCAN_FILES = [
    *SRC.glob("features/*/presentation/schemas.py"),
    *SRC.glob("features/*/domain/models.py"),
]


def _class_field_names(tree: ast.AST):
    """클래스 본문 직속의 속성/필드명 (모델 Column, 스키마·dataclass 필드)."""
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        for stmt in node.body:
            if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                yield stmt.target.id, stmt.lineno
            elif isinstance(stmt, ast.Assign):
                for t in stmt.targets:
                    if isinstance(t, ast.Name):
                        yield t.id, stmt.lineno


def check_file(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"), str(path))
    return [
        (lineno, name)
        for name, lineno in _class_field_names(tree)
        if name.endswith(FORBIDDEN) and name not in ALLOWLIST
    ]


def main() -> int:
    files = [p for d in SCAN_DIRS for p in d.glob("*.py")] + SCAN_FILES
    violations = []
    for path in sorted(set(files)):
        for lineno, name in check_file(path):
            violations.append((path.relative_to(SRC.parent), lineno, name))

    if violations:
        print("네이밍 위반 — 속성/필드명이 DB 전용 접미어로 끝남 (친화명으로 바꾸세요):")
        for rel, lineno, name in violations:
            print(f"  {rel}:{lineno}  {name}  → 접미어 제거 (예: status_cd→status, read_yn→is_read)")
        print(f"\n{len(violations)}건. DB 컬럼명은 Column(\"{name}\", …) 문자열로 보존하면 됩니다.")
        return 1
    print("네이밍 OK — 응답에 새는 DB 접미어 없음.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
