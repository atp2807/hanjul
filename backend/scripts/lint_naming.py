#!/usr/bin/env python3
"""네이밍 린터 — 접미어 규칙 2방향 CI 게이트.

정책 출처: 공용 네이밍 사전 ``naming_dic/dictionary.json`` (규칙 db_column_suffix·
amount_suffix, 필드 status_cd "ORM에서는 status로 매핑"). CI 자체완결(별도 레포
naming_dic 미체크아웃)을 위해 정책을 여기 vendored — naming_dic 갱신 시 동기화.

검사 1) 응답 누출 — 모델 속성·스키마 필드·도메인 View 필드가 _cd·_yn·_ts·_dt 로
   끝나면 위반 (→ status·is_read·created_at 친화명). DB 컬럼명 Column("status_cd")
   문자열은 대상 아님. 금액 _amt·번호 _no 는 허용(API 유지).
검사 2) DB 컬럼 접미어 — 컬럼명(모델 Column("…")·bare 속성·마이그레이션)이 장황한
   형태(_amount·_code·_number…)면 위반 (→ _amt·_cd·_no 사전 접미어).
"""
import ast
import sys
from pathlib import Path

# [검사1] 속성/필드명에서 금지하는 "DB 전용" 접미어.
FORBIDDEN = ("_cd", "_yn", "_ts", "_dt")
# 예외 — 순수 내부(응답 미노출)+rename이 지역변수와 얽혀 위험. 신규 추가 지양.
ALLOWLIST = {"provider_cd"}  # OAuth 제공자 코드. auth_service 지역변수 충돌.

# [검사2] DB 컬럼명이 장황한 형태면 사전 접미어로. (wrong → right)
WRONG_SUFFIX = {
    "_amount": "_amt", "_count": "_cnt", "_number": "_no", "_code": "_cd",
    "_date": "_dt", "_timestamp": "_ts", "_time": "_ts",
}

SRC = Path(__file__).resolve().parent.parent / "src"
MIGRATIONS = Path(__file__).resolve().parent.parent / "migrations" / "versions"
SCAN_MODELS = [SRC / "infrastructure" / "db" / "models"]
SCAN_SCHEMAS = [
    *SRC.glob("features/*/presentation/schemas.py"),
    *SRC.glob("features/*/domain/models.py"),
]


def _is_column_call(func) -> bool:
    return (isinstance(func, ast.Name) and func.id == "Column") or (
        isinstance(func, ast.Attribute) and func.attr == "Column"
    )


def _class_fields(tree):
    """클래스 본문 직속 속성/필드 (name, lineno, value_node)."""
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        for stmt in node.body:
            if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                yield stmt.target.id, stmt.lineno, stmt.value
            elif isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name):
                yield stmt.targets[0].id, stmt.lineno, stmt.value


def check_response_leak(path: Path):
    """검사1 — 속성/필드명이 _cd·_yn·_ts·_dt 로 끝남."""
    tree = ast.parse(path.read_text(encoding="utf-8"), str(path))
    return [
        (lineno, name, "속성/필드명 접미어 (→ 친화명, 예: status_cd→status)")
        for name, lineno, _ in _class_fields(tree)
        if name.endswith(FORBIDDEN) and name not in ALLOWLIST
    ]


def _column_name(name, value):
    """이 속성이 컬럼이면 DB 컬럼명 반환 — Column("literal") 있으면 그 문자열, 없으면 속성명."""
    if isinstance(value, ast.Call) and _is_column_call(value.func):
        if value.args and isinstance(value.args[0], ast.Constant) and isinstance(value.args[0].value, str):
            return value.args[0].value
        return name
    return None


def check_column_suffix(path: Path, migration: bool = False):
    """검사2 — DB 컬럼명이 장황한 접미어(_amount·_code…)."""
    tree = ast.parse(path.read_text(encoding="utf-8"), str(path))
    cols = []
    if migration:
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and _is_column_call(node.func)
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ):
                cols.append((node.args[0].value, node.lineno))
    else:
        for name, lineno, value in _class_fields(tree):
            col = _column_name(name, value)
            if col:
                cols.append((col, lineno))
    out = []
    for col, lineno in cols:
        for wrong, right in WRONG_SUFFIX.items():
            if col.endswith(wrong):
                out.append((lineno, col, f"DB 컬럼 접미어 {wrong}→{right}"))
    return out


def main() -> int:
    violations = []
    for d in SCAN_MODELS:
        for p in d.glob("*.py"):
            for lineno, name, why in check_response_leak(p) + check_column_suffix(p):
                violations.append((p.relative_to(SRC.parent), lineno, name, why))
    for p in SCAN_SCHEMAS:
        for lineno, name, why in check_response_leak(p):
            violations.append((p.relative_to(SRC.parent), lineno, name, why))
    if MIGRATIONS.exists():
        for p in MIGRATIONS.glob("*.py"):
            for lineno, name, why in check_column_suffix(p, migration=True):
                violations.append((p.relative_to(SRC.parent.parent), lineno, name, why))

    if violations:
        print("네이밍 위반:")
        for rel, lineno, name, why in sorted(set(violations)):
            print(f"  {rel}:{lineno}  {name}  — {why}")
        print(f"\n{len(set(violations))}건. DB 컬럼명은 Column(\"db_name\", …)로 접미어 보존.")
        return 1
    print("네이밍 OK — 응답 누출·DB 컬럼 접미어 모두 규칙 준수.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
