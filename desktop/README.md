# 한줄 IDE — 데스크탑 (P1, Host Port v0)

한줄 IDE 웹뷰 앱(`packages/ide-core`)을 macOS(pywebview/WKWebView) 위에 띄우고,
SQLite 기반 Host Port v0(`desktop/store.py`)로 책/챕터를 영속한다.

설계 정본: LinkLore `dc-73539bba`("웹뷰 앱은 하나, 호스트는 둘" — 데스크탑(pywebview)과
모바일(RN WebView, P2)이 `packages/ide-core` 동일 번들을 로드하고, 호스트(저장/동기화)만
플랫폼별로 교체). Host Port 계약 전문은 `packages/ide-core/HOST_PORT.md`.

이전 P0 스파이크(`desktop/webapp/` — 파일 하나짜리 저장, react 없는 최소 vite 앱)는
`packages/ide-core` 로 대체되어 삭제됐다(git 이력에는 남아있음).

## 준비

```bash
# 1) 웹뷰 앱 빌드 — 저장소 루트에서 (packages/* 는 루트 workspaces 에 편입됨)
cd /path/to/hanjul
npm install
npm run build -w packages/ide-core   # packages/ide-core/dist/ 산출 — pywebview 가 이걸 로드

# 2) 데스크탑 파이썬 환경
cd desktop
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt          # 런타임(pywebview)
.venv/bin/pip install -r requirements-dev.txt       # + pytest(테스트용)
```

`packages/ide-core/src/`를 고치면 `npm run build -w packages/ide-core` 를 다시 돌려야
`app.py` 가 보는 `dist/`에 반영된다(pywebview 는 `dist/index.html` 을 직접 로드하지,
vite dev 서버를 띄우지 않는다).

## 실행

```bash
cd desktop
.venv/bin/python app.py            # GUI 창 — 아래 IME 체크리스트를 수행
.venv/bin/python app.py --smoke    # 자동 스모크(수 초 내 종료, stdout 에 SMOKE_RESULT 한 줄)
.venv/bin/python app.py --db /tmp/foo.db  # 대체 DB 경로(검증/반복 실행용, 기본은 data/ide.db)
```

데이터는 `desktop/data/ide.db`(SQLite, gitignore)에 쌓인다. 첫 실행 시 기본 책 1권 +
빈 챕터 1개가 자동 생성된다(`store.py` 의 `_ensure_seed`, 멱등 — 재실행해도 중복 생성 안 함).

## 테스트

```bash
cd desktop && .venv/bin/pip install -r requirements-dev.txt   # 최초 1회
.venv/bin/python -m pytest desktop/tests -q   # 저장소 루트에서, 또는
cd desktop && .venv/bin/python -m pytest tests -q   # desktop/ 에서
```

`desktop/conftest.py` 가 `desktop/`를 sys.path 에 등록해 `import store` 가 되게 한다
(패키지화 없이 stdlib 스타일 모듈 하나로 유지하기 위함).

## 로그인 (P1 슬라이스5, 시스템 브라우저 + OS 키체인)

상단바 [로그인]을 누르면 데스크탑 표준 패턴(RFC 8252)대로 동작한다:

1. 앱이 127.0.0.1의 임시 포트에 1회용 HTTP 리스너를 연다.
2. 시스템 브라우저로 `GET /api/auth/google/login?next=http://127.0.0.1:<port>/callback`이
   돌려준 실제 Google 인가 URL을 연다(`desktop/auth_flow.py`).
3. Google 로그인 완료 → 백엔드 콜백이 그 루프백 주소로 `?token=...`을 리다이렉트 →
   리스너가 받아 파싱하고 즉시 창을 닫아도 된다는 안내 HTML을 보여준다.
4. 받은 토큰을 OS 키체인(macOS Keychain 등, `keyring` 패키지)에 저장한다 —
   `desktop/token_store.py`, 서비스명 `hanjul-ide`. 이제부터 [발행]/`whoami()`는 이
   토큰을 keyring에서 우선 조회한다(비어있으면 아래 "토큰 수동 입력" 평문 폴백으로 내려감).

**keyring이 없는 환경(예: headless Linux)**: `login()`이 저장 시 `KeyringUnavailableError`를
그대로 던진다(조용한 평문 폴백 없음) — 이런 환경은 아래 "토큰 수동 입력"으로 대신한다.

**실 Google OAuth 자격증명이 없는 로컬 개발 환경**에서 로그인 버튼은 실제 Google 페이지까지는
뜨지만 완료할 수 없다(`GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET` 필요). 이 경우 루프백
리스너/브리지 자체는 `desktop/tests/test_auth_flow.py`(가짜 리다이렉트)로 이미 검증되어
있고, 백엔드까지 포함한 실제 왕복을 손으로 확인하려면 아래처럼 `E2E_LOGIN_ENABLED` 우회를
쓴다(자동화하지 않음 — 실 브라우저를 여는 경로라 수동 검증용):

```bash
# 1) 로컬 백엔드 — 마이그레이션 + E2E 로그인 우회 켜고 기동 (.venv312, 3.12/asyncpg 필수)
cd backend && .venv312/bin/alembic upgrade head
cd backend && E2E_LOGIN_ENABLED=1 .venv312/bin/uvicorn main:app --host 127.0.0.1 --port 28000

# 2) GUI 에서: 상단바 [설정] → apiBase=http://127.0.0.1:28000 저장(토큰은 비워둠).
# 3) 로그인 버튼을 누르면 리스너가 열리고 시스템 브라우저가 실제 Google URL을 연다
#    (자격증명이 없어 실패해도 무방) — 그 사이 별도 터미널에서 test-login에 같은
#    next(브라우저에 뜬 Google URL의 redirect_uri 파라미터에서 포트 확인)를 직접 쏴서
#    콜백을 채운다:
#    curl "http://127.0.0.1:28000/api/auth/test-login?email=me@example.com&next=http://127.0.0.1:<포트>/callback"
#    → 데스크탑 앱이 토큰을 받아 keyring에 저장하고 상단바에 이메일이 표시된다.
```

## 발행 — 로컬 백엔드로 테스트하는 법 (P1 슬라이스4)

`publisher.py`가 로컬 책을 hanjul 백엔드 출판 API로 밀어넣는다. 인증은 위 [로그인]으로
받은 토큰(keyring)을 우선 쓰고, 없으면 **토큰 수동 입력**(설정 버튼 → apiBase/token
직접 입력, P1 슬라이스4 시절 폴백 — 여전히 동작)으로 내려간다.
`desktop/tests`의 pytest 는 stdlib `http.server` 기반 Fake 서버로만 검증하고(네트워크 X,
`--smoke`도 발행은 제외), 진짜 백엔드로 발행이 되는지는 아래 절차로 손으로 확인한다.

```bash
# 1) 로컬 백엔드 — 마이그레이션 + E2E 로그인 우회 켜고 기동 (.venv312, 3.12/asyncpg 필수)
cd backend && .venv312/bin/alembic upgrade head
cd backend && E2E_LOGIN_ENABLED=1 .venv312/bin/uvicorn main:app --host 127.0.0.1 --port 28000

# 2) GUI 에서 손으로 — 둘 중 하나:
#    a) 상단바 [로그인] 클릭(위 "로그인" 절 참고, 실 Google 자격증명 필요) 또는
#    b) 토큰 수동 입력(자격증명 없을 때): 상단바 [설정] → apiBase=http://127.0.0.1:28000,
#       token= 아래 URL을 브라우저로 열어 리다이렉트 fragment(#token=...)에서 복사
#       http://127.0.0.1:28000/api/auth/test-login?email=me@example.com
#    → 상단바 [발행] 클릭. 신규 책이라 가격이 없으므로 422("가격을 먼저 설정해야
#    해요")가 정상 — 이 슬라이스는 가격 설정 UI가 없다(publisher.py 모듈 docstring
#    "미해결" 참고). 웹 스튜디오에서 해당 책 가격을 설정한 뒤 재발행하면 통과한다.

# 3) 또는 GUI 없이 스크립트로 전 과정(토큰 발급 포함) 자동 확인 — opt-in, 평소엔 안내만:
cd desktop && RUN_PUBLISH_LIVE=1 .venv/bin/python scripts/publish_live.py
```

`scripts/publish_live.py`는 사용자의 실제 `desktop/data/ide.db`(작업 중인 원고)를 전혀
건드리지 않는다 — 매번 임시 SQLite에 책 1권 + 검증용 문단을 새로 만들어 발행한다.

## 구조

- `packages/ide-core/` — 웹뷰 앱 본체(에디터+챕터 사이드바+호스트 브리지 클라이언트).
  `@hanjul/doc` 의 `mountEditor` 를 상대경로로 직접 import 한다(react 배럴을 거치지
  않기 위해 — P0 스파이크와 동일 이유). 자세한 계약은 `packages/ide-core/HOST_PORT.md`.
- `store.py` — SQLite 저장소. 테이블: `book(id, title, created_ts, updated_ts,
  remote_book_id)`, `chapter(id, book_id, title, synopsis, status_cd, order_no, html,
  created_ts, updated_ts)`, `setting(key, value)`. 신규 테이블은
  `CREATE TABLE IF NOT EXISTS` 멱등, 기존 테이블에 컬럼 추가(`remote_book_id`)는
  `PRAGMA table_info` 확인 후 `ALTER TABLE`(멱등 헬퍼 `_ensure_column`).
- `app.py` — pywebview 셸. `js_api=Api(store)` 로 Host Port v0 8개 메서드
  (`get_book`/`list_chapters`/`load_chapter`/`save_chapter`/`create_chapter`/
  `delete_chapter`/`reorder_chapters`/`import_file`) + 발행 3종(P1 슬라이스4,
  `get_settings`/`save_settings`/`publish`) + 인증 3종(P1 슬라이스5,
  `login`/`logout`/`whoami`)을 노출. 웹앱 로드 대상은 `packages/ide-core/dist/index.html`.
- `auth_flow.py` — 시스템 브라우저 로그인 플로우(P1 슬라이스5, RFC 8252). 127.0.0.1
  임시 포트에 1회용 HTTP 리스너를 열고, 콜백(`?token=...&isNew=...`)을 파싱한다.
  `webbrowser.open()`/실 백엔드 없이도(가짜 콜백 주입) 리스너 로직만 결정적으로 테스트
  가능(`tests/test_auth_flow.py`).
- `token_store.py` — 로그인 토큰의 OS 키체인 보관(P1 슬라이스5, `keyring` 패키지).
  서비스명 `hanjul-ide`. 백엔드 자체가 없는 환경은 `KeyringUnavailableError`를 명시적으로
  던진다(조용한 평문 폴백 없음) — `app.py`의 `_effective_token()`이 keyring 우선·
  `store.py`의 평문 `setting.token`(dev 수동 입력) 폴백 순서로 조회.
- `importer.py` — 원고 가져오기(P1 슬라이스3, TXT/MD/DOCX/HWP/HWPX). backend/src/engine/doc
  의 순수 파이썬 파서를 그대로 재사용해 UniversalDoc → 정본 HTML을 만들고, h1 경계로
  챕터 목록(`[{"title", "html"}, ...]`)을 분리한다. backend 코드는 수정하지 않는다.
- `publisher.py` — 발행 연결(P1 슬라이스4). 로컬 챕터 html을 `backend/src/engine/doc`의
  `parse_dialect`/`serialize_doc`로 되읽어 서버 `{type,html}` 블록으로 바꾸고(h1 경계는
  `importer.py`의 `_split_by_h1` 재사용), `backend/src/engine/imports/block_html.py`의
  `validate_block_html`을 그대로 import 해 프리플라이트한다(새 검증기 없음, drift 0).
  HTTP는 stdlib `urllib`만 사용(의존성 추가 없음).
- `scripts/publish_live.py` — 실 로컬 백엔드로 발행해보는 opt-in 수동 검증 스크립트
  (`RUN_PUBLISH_LIVE=1`). 아래 "발행" 절 참고.
- `tests/test_store.py` — `store.py` CRUD/재배열/시드 멱등성 단위 테스트(pytest,
  tmp_path 로 격리된 sqlite 파일 사용 — `data/ide.db` 를 건드리지 않음).
- `tests/test_publisher.py` — `publisher.py` 단위 테스트. HTTP는 stdlib `http.server`
  기반 Fake 서버로(요청 경로·헤더·바디 실측 단언), 프리플라이트 위반 케이스, store
  마이그레이션(`remote_book_id` 컬럼) 멱등성까지 검증. 실 백엔드는 띄우지 않는다.
- `tests/test_auth_flow.py` — `auth_flow.py` 단위 테스트. 실 소켓(127.0.0.1)으로 리스너를
  열고 진짜 HTTP 요청(가짜 리다이렉트 hit)으로 토큰 파싱·1회성·타임아웃·잡음 요청 무시를
  검증. 실 브라우저/백엔드는 띄우지 않는다.
- `tests/test_token_store.py` — `token_store.py` 단위 테스트. `keyring.get_password`/
  `set_password`/`delete_password`를 인메모리 dict로 monkeypatch — 실 OS 키체인은
  절대 건드리지 않는다.
- `tests/test_app.py` — `app.py`의 `login`/`logout`/`whoami` + 토큰 소스 우선순위
  (keyring 우선·평문 폴백) 오케스트레이션 테스트. `_request`/`run_login_flow`/
  `get_token`/`set_token`/`delete_token`을 monkeypatch.
- `data/` — 실행 시 생성되는 SQLite 파일(gitignore, 커밋 안 함).

## 한글 IME 수동 체크리스트 (GUI 창에서)

에디터 영역을 클릭해 포커스를 준 뒤 아래를 순서대로 확인하고, 이상 있으면 정확히
어떤 단계에서 어떻게 깨졌는지 기록한다. (P0 스파이크에서 이미 통과 확인됨 — 회귀
여부만 눈으로 재확인하면 된다.)

1. **조합 입력** — "안녕하세요"를 타이핑. 자모가 정상적으로 결합되는가(ㅇ+ㅏ+ㄴ→안
   처럼 중간 조합 상태가 자연스럽게 넘어가는가), 완성형이 아닌 낱자모가 남지 않는가.
2. **빠른 연타** — 손이 가는 대로 빠르게(1000타 수준 흉내) 문단 하나를 타이핑. 글자
   깨짐·중복 입력·순서 뒤바뀜이 없는가.
3. **조합 중 백스페이스** — 자모를 조합하는 도중(예: "가" 입력 중 "ㄱㅏ" 상태)
   백스페이스를 눌러 지운다. 조합 중이던 글자가 깨끗이 지워지는가, 커서 위치가
   튀지 않는가.
4. **조합 중 다른 위치 클릭** — 한글 조합 중(완성되지 않은 상태)에 마우스로 문서의
   다른 위치를 클릭. 조합 중이던 글자가 유실되거나 잘못된 위치에 커밋되지 않는가.
5. **긴 문단 붙여넣기** — 다른 곳에서 복사한 긴 한글 문단을 붙여넣기(Cmd+V). 방언
   정규화(`dialect.js`) 를 거쳐 삽입되는데, 한글 텍스트 자체가 깨지지 않는가.
6. **서식 후 이어서 입력** — 툴바에서 굵게(B)/기울임(I) 을 누른 뒤 바로 이어서 한글을
   입력. 서식 토글 직후에도 IME 조합이 정상 동작하는가(포커스/커서 유실 없는가).

## 자동 스모크가 확인하는 것 / 확인하지 않는 것

`--smoke` 는 다음을 결정적으로 확인한다:
- **마운트**: `mountApp()` 완료(`window.__ideApp` 존재) 및 `[contenteditable]`
  요소가 DOM 에 존재하는가.
- **Host Port CRUD 왕복**: `createChapter` → `saveChapter(html)` →
  `reorderChapters` → (프로세스 재시작 없이) `listChapters` 로 순서 재확인,
  `loadChapter` 로 상태/내용 재확인까지 전부 실제 SQLite 왕복으로 검증한다.
- **원고 가져오기(P1 슬라이스3)**: h1 2개짜리 임시 .md 를 만들어 `import_file(path)` 로
  왕복(다이얼로그는 path 인자로 건너뜀) — 챕터 2개 추가·각 h1 텍스트가 제목이 됐는지·
  본문이 일치하는지까지 실제 SQLite 왕복으로 검증한다(`SMOKE_RESULT` 의 `import_result`).

**발행(P1 슬라이스4)은 스모크에서 의도적으로 제외**했다 — 실 네트워크 호출(백엔드
기동)이 필요해 "수 초 내 결정적으로 끝나는" 스모크의 전제와 안 맞는다. 대신
`tests/test_publisher.py`(Fake 서버, 네트워크 없이 결정적)로 단위 검증하고, 진짜
서버 왕복은 opt-in `scripts/publish_live.py`로 손으로 확인한다(위 "발행" 절).

IME 조합 자체(자모 결합·타이밍·커서 이동)는 **사람 손으로만** 확인 가능하다 —
헤드리스로 키 이벤트를 흉내내는 건 실제 OS IME 엔진 경로를 타지 않아 목적(WKWebView
실환경 검증)과 어긋난다. 그래서 자동화하지 않았다.

## 브리지 비동기 관련 메모 (lr-9a45e6e4)

`window.pywebview.api.*` 호출은 JS 쪽에서 **Promise** 를 반환하고, 실제 Python
메서드는 별도 스레드에서 실행된다(pywebview `util.js_bridge_call`). `evaluate_js` 로
그 Promise 를 콜백 없이 동기 확인하면 처리가 끝나기 전에 빈 값("{}")을 읽어버리는
레이스가 생긴다 — 그래서 `app.py` 의 스모크는 JS 쪽에 완료 플래그
(`window.__smokeDone`/`window.__smokeResult`, 마운트 확인용 `window.__ideApp`)를
심어 그 플래그가 설 때까지 폴링한다. 앞으로 Host Port 브리지 코드를 건드릴 때도
이 규칙을 그대로 따른다 — evaluate_js 로 async 결과를 직접 받지 말 것.

`packages/ide-core/src/host.js` 자체는 이 문제와 무관하다 — 거기서
`window.pywebview.api.xxx(...)` 를 직접 `await` 하는 건 pywebview 가 제공하는 정상
Promise 경로다. 레이스는 오직 "Python(app.py) 쪽에서 evaluate_js 로 그 비동기 결과를
훔쳐보려 할 때"만 발생한다.
