#!/usr/bin/env bash
# 한줄 IDE 데스크탑 번들 빌드 — 웹뷰 앱(packages/ide-core) 빌드 → PyInstaller 번들.
#
# 순서가 중요하다: hanjul_ide.spec 이 packages/ide-core/dist/(vite 산출물)를 데이터로
# 그대로 긁어가므로, pyinstaller 전에 반드시 최신 dist/ 가 있어야 한다(app.py 가 로드하는
# index.html/perf.html/assets 가 여기서 나온다).
#
# 사용:
#   desktop/scripts/build_bundle.sh              # PyInstaller 는 desktop/.venv 안에서 찾음
#   PYINSTALLER=pyinstaller desktop/scripts/build_bundle.sh   # PATH 의 다른 pyinstaller 강제
#
# 산출물: desktop/dist/hanjul_ide/ (onedir), macOS 는 그 안에 HanjulIDE.app 도 함께 생김
# (COLLECT 산출물 폴더 안에 BUNDLE 이 만들어 넣는다 — hanjul_ide.spec 참고).
# 공증·코드사이닝은 범위 밖 — 서명 없는 번들이 실행되는 것까지만 확인한다.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DESKTOP_DIR="$(dirname "$SCRIPT_DIR")"
REPO_ROOT="$(dirname "$DESKTOP_DIR")"

echo "== 1) 웹뷰 앱 빌드 (packages/ide-core) =="
cd "$REPO_ROOT"
npm run build -w packages/ide-core

echo "== 2) PyInstaller 번들 =="
cd "$DESKTOP_DIR"

if [ -n "${PYINSTALLER:-}" ]; then
  PYINSTALLER_BIN="$PYINSTALLER"
elif [ -x "$DESKTOP_DIR/.venv/bin/pyinstaller" ]; then
  PYINSTALLER_BIN="$DESKTOP_DIR/.venv/bin/pyinstaller"
elif command -v pyinstaller >/dev/null 2>&1; then
  PYINSTALLER_BIN="pyinstaller"
else
  echo "pyinstaller 를 찾을 수 없어요. 먼저 설치하세요:" >&2
  echo "  cd desktop && .venv/bin/pip install pyinstaller pyinstaller-hooks-contrib" >&2
  exit 1
fi

echo "사용할 pyinstaller: $PYINSTALLER_BIN"
"$PYINSTALLER_BIN" hanjul_ide.spec --noconfirm --clean

echo "== 완료: $DESKTOP_DIR/dist/hanjul_ide/ =="
