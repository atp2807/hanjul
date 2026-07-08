# -*- mode: python ; coding: utf-8 -*-
"""한줄 IDE — PyInstaller onedir 번들 spec (서명·공증 범위 밖, 로컬 실행까지만).

빌드:
    cd desktop && pyinstaller hanjul_ide.spec        # 또는 scripts/build_bundle.sh
산출물: desktop/dist/hanjul_ide/ (onedir) — macOS 는 그 안에 hanjul_ide.app 도 함께 생김
        (COLLECT 산출물 폴더 안에 BUNDLE 이 .app 을 만들어 넣는다).

onedir 을 쓰는 이유(onefile 대신): onefile 은 실행 시마다 임시 폴더에 압축을 풀고 그
안에서 돌아가는데, pywebview 의 웹뷰 리소스(특히 macOS WKWebView 로드 대상인
packages/ide-core/dist/index.html 과 그 상대경로 assets/)가 매 실행 재해제되는 임시
경로에 걸리면 상대경로 문제가 생기기 쉽고, 시작 속도도 느려진다 — onedir 이 pywebview
데스크탑 앱에 흔히 권장되는 이유와 동일.

포함 대상 근거(무엇을 왜 담았는지):
- entry point = desktop/app.py 하나 — auth_flow.py/backup.py/importer.py/publisher.py/
  store.py/token_store.py 는 app.py 와 같은 폴더(desktop/)에 있는 형제 모듈이라
  PyInstaller 가 entry script 폴더를 자동으로 탐색 경로에 넣어준다(별도 pathex 불필요).
- pathex 에 backend/ 를 추가 — desktop/importer.py:58-60, desktop/publisher.py:58-60 가
  런타임에 ``sys.path.insert(0, backend/)`` 후 ``from src.engine.doc... import`` 하는
  모노레포 참조 패턴(backend/conftest.py:5 와 동일)을 쓴다. PyInstaller 의 정적 분석
  (modulegraph)은 이 sys.path 조작을 실행하지 않으므로, 같은 효과를 내려면 Analysis
  에도 동일한 디렉터리를 pathex 로 줘야 ``from src.engine...`` import 문을 정적으로
  풀어 backend/src 이하 필요한 모듈만 추릴 수 있다(전체 backend/src 를 통째로 넣는
  대신, 실제 import 그래프만 자동으로 따라간다 — 아래 실측 참고).
- 실제로 딸려 들어가는 backend 모듈은 정확히 이만큼이다(2026-07-08 실측, grep으로
  import 그래프 확인 — desktop/importer.py, desktop/publisher.py, desktop/backup.py
  가 참조하는 것 전부):
    src/__init__.py, src/engine/__init__.py, src/engine/doc/__init__.py (전부 빈 파일)
    src/engine/doc/models.py, src/engine/doc/dialect.py
    src/engine/doc/parsers/__init__.py (빈 파일)
    src/engine/doc/parsers/{docx,hwp,hwpx,markdown,text,_ole2}.py
    src/engine/imports/__init__.py (빈 파일), src/engine/imports/block_html.py
  이 파일들은 전부 stdlib 만 쓴다(dataclasses/enum/io/re/zipfile/html/xml.etree/
  struct/zlib — grep 실측, desktop/importer.py 모듈독스트링에 상세 인용 있음).
  ``backend/src/engine/doc/ingest.py``(10 포맷 전체 레지스트리, pdfminer 등 요구)는
  desktop 쪽에서 애초에 import 하지 않으므로 이 spec 도 그걸 끌어오지 않는다 —
  ``base.py``(Protocol 정의, 파서들이 실제로 import 하지 않음)도 마찬가지로 제외된다.
  즉 backend/ 전체를 데이터로 욱여넣지 않고, "실제 import 그래프만" 정적 분석이
  자동으로 골라 담는다(pathex 는 탐색 경로만 넓힐 뿐 강제 포함이 아님).
- packages/ide-core/dist/ 를 datas 로 포함 — desktop/app.py 가 pywebview 창에 로드하는
  index.html(+ perf.html, assets/)이 여기 있다. 프로즌 실행 시 ``sys._MEIPASS``
  (onedir 은 실행파일과 같은 폴더) 바로 아래 ``packages/ide-core/dist/`` 로 심어
  app.py 의 frozen 분기(ASSETS_ROOT = Path(sys._MEIPASS) if sys.frozen else ...)가
  그대로 찾게 했다.
- ``keyring`` — token_store.py(P1 슬라이스5, 로그인 토큰의 OS 키체인 저장)가 쓴다.
  ``keyring.backend._load_plugins()``(desktop/.venv/lib/python3.14/site-packages/
  keyring/backend.py:241)가 ``importlib.metadata.entry_points(group="keyring.backends")``
  로 백엔드 모듈(macOS/SecretService/Windows/chainer/kwallet/libsecret)을 **동적으로**
  import 한다 — 일반 import 문이 아니라 PyInstaller 정적 분석이 못 따라간다. 그래서:
    1) ``collect_submodules("keyring.backends")`` 로 그 백엔드 모듈들을 hiddenimports 에
       명시(실제 파일이 없으면 빌드 로그에 "not found" 경고만 뜨고 무시됨 — 예: pywin32
       가 없는 이 macOS 빌드 환경에서 Windows 백엔드가 그렇다. 무해 — 각 OS 는 자기
       백엔드만 실제로 쓴다).
    2) ``copy_metadata("keyring")`` 로 keyring 의 dist-info(entry_points.txt 포함)를
       번들에 그대로 복사 — 이게 없으면 번들 안에서 ``entry_points(group=...)`` 가
       빈 결과를 내 macOS Keychain 백엔드 자체가 아예 로드되지 않는다.
  ※ 실측(2026-07-08, PyInstaller 6.21.0): PyInstaller 코어가 최근
  ``PyInstaller/hooks/hook-keyring.py`` 를 자체 내장해 위 두 가지를 이미 자동으로
  해준다(빌드 로그에 "Processing standard module hook 'hook-keyring.py'" 로 확인) —
  그래도 이 spec 은 명시적으로 남겨둔다(더 오래된/다른 PyInstaller 배포에도 동일하게
  동작하도록, 버전에 의존하지 않기 위해 — 중복돼도 무해, collect_submodules/
  copy_metadata 는 멱등).
  macOS 백엔드(keyring/backends/macOS/api.py)는 pyobjc 가 아니라 ctypes 로 Security.
  framework 를 직접 호출해(실측: import 문에 ctypes/ctypes.util 만 있음) 별도
  hiddenimport 없이 그대로 동작한다.
- pywebview 자체는 별도 조치가 필요 없다 — ``webview/guilib.py`` 의 플랫폼 선택은
  ``import webview.platforms.cocoa as guilib`` 같은 **일반 import 문**(try/except 안에
  있을 뿐 실제로는 정적으로 보이는 IMPORT_NAME)이라 PyInstaller 가 알아서 따라가고,
  pywebview 패키지 자체가 ``__pyinstaller/hook-webview.py`` 를 내장해 JS 브릿지 자산을
  자동 수집한다(``webview/__pyinstaller/__init__.py`` 의 ``get_hook_dirs()`` 로 PyInstaller
  가 엔트리포인트 없이도 자동 탐색). cocoa.py 가 쓰는 AppKit/Foundation/WebKit/objc/
  PyObjCTools 도 전부 실제 import 문이라 각자 설치된 pyobjc 패키지를 그대로 따라간다.
"""

import os

from PyInstaller.utils.hooks import collect_submodules, copy_metadata

REPO_ROOT = os.path.dirname(SPECPATH)  # noqa: F821 (PyInstaller 가 spec 실행 시 주입)
BACKEND_DIR = os.path.join(REPO_ROOT, "backend")
IDE_CORE_DIST = os.path.join(REPO_ROOT, "packages", "ide-core", "dist")

if not os.path.isdir(IDE_CORE_DIST):
    raise SystemExit(
        f"빌드 산출물 없음: {IDE_CORE_DIST}\n"
        "먼저 저장소 루트에서 `npm install && npm run build -w packages/ide-core` 를 실행하세요."
    )

hiddenimports = collect_submodules("keyring.backends")
datas = copy_metadata("keyring")
datas += [(IDE_CORE_DIST, os.path.join("packages", "ide-core", "dist"))]

block_cipher = None

a = Analysis(  # noqa: F821
    [os.path.join(SPECPATH, "app.py")],  # noqa: F821
    pathex=[BACKEND_DIR],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    cipher=block_cipher,
)
pyz = PYZ(a.pure, cipher=block_cipher)  # noqa: F821

exe = EXE(  # noqa: F821
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="hanjul_ide",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    # console=False — 실제 사용자용 GUI 앱이라 창이 있는 앱으로 뜨는 게 맞다(console=True 로
    # 빌드해보니 BUNDLE() 이 Info.plist 에 LSBackgroundOnly=true 를 자동으로 넣어 Dock 아이콘
    # 없이 백그라운드로만 뜨는 문제가 실측됐다 — 2026-07-08, dist/HanjulIDE.app/Contents/
    # Info.plist 확인). onedir 실행파일(dist/hanjul_ide/hanjul_ide)을 터미널에서 직접
    # 실행하면 console 설정과 무관하게 stdout 이 그대로 보인다(macOS 는 console 플래그가
    # Windows 처럼 표준입출력을 가로채지 않는다 — 직접 실행 시 실측 확인됨) — 그래서
    # --smoke 검증은 이 경로로 한다.
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,  # 서명 범위 밖 — 서명 없는 실행까지만.
    entitlements_file=None,
)
coll = COLLECT(  # noqa: F821
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="hanjul_ide",
)

# macOS 전용 — .app 번들(COLLECT 산출물 폴더 안에 생성). 다른 플랫폼에서 pyinstaller 를
# 돌리면 BUNDLE() 은 그냥 아무 효과가 없다(darwin 이 아니면 스킵).
app = BUNDLE(  # noqa: F821
    coll,
    name="HanjulIDE.app",
    icon=None,
    bundle_identifier="io.hanjul.ide",
    info_plist={
        "CFBundleName": "한줄 IDE",
        "CFBundleDisplayName": "한줄 IDE",
        "NSHighResolutionCapable": True,
    },
)
