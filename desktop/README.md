# 한줄 IDE — P0 스파이크 ⓐ

목적: **macOS WKWebView(pywebview)에서 한글 IME 입력이 정상인가**를 사람이 손으로
확인할 수 있는 최소 실행물. `packages/doc`(한줄독 코어)의 `mountEditor` contenteditable
에디터를 pywebview 셸 안에 그대로 띄우고, JS↔Python 브리지(자동저장) 왕복을 확인한다.

이 디렉터리는 루트 npm workspaces(`packages/*`, `web`, `potato`)에 편입되지 않은
독립 프로젝트다. 루트 `package.json`/lockfile 은 건드리지 않는다.

## 준비

```bash
cd desktop
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

cd webapp
npm install
npm run build      # dist/ 산출 — pywebview 가 이걸 로드한다
```

## 실행

```bash
cd desktop
.venv/bin/python app.py            # GUI 창 — 아래 IME 체크리스트를 수행
.venv/bin/python app.py --smoke    # 자동 스모크(수 초 내 종료, stdout 에 SMOKE_RESULT 한 줄)
```

`webapp/src/`를 고치면 `npm run build` 를 다시 돌려야 `app.py` 가 보는 `dist/`에 반영된다
(pywebview 는 `webapp/dist/index.html` 을 직접 로드하지, vite dev 서버를 띄우지 않는다).

## 구조

- `webapp/` — 최소 vite 프로젝트(React 없음). `packages/doc/src/editor.js` 의
  `mountEditor(el, opts)` 를 상대경로로 직접 import 해서 씁니다(워크스페이스 편입 없이).
- `app.py` — pywebview 앱. `js_api=Api()` 로 `save_chapter(html)` 을 JS 쪽에
  `window.pywebview.api.save_chapter` 로 노출. 저장은 `spike_data/chapter.html` 파일
  하나에 덮어쓰기(SQLite 는 P1 — 스파이크는 파일로 충분).
- `spike_data/` — 실행 시 생성되는 저장 산출물(gitignore, 커밋 안 함).

## 한글 IME 수동 체크리스트 (GUI 창에서)

에디터 영역을 클릭해 포커스를 준 뒤 아래를 순서대로 확인하고, 이상 있으면 정확히
어떤 단계에서 어떻게 깨졌는지 기록한다.

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

문제가 재현되면: 어떤 단계 · 어떤 문자열 · 재현 빈도(매번/가끔) · 캡처 가능하면 화면
녹화를 남겨서 다음 스파이크(ⓑ 등)에 근거로 넘긴다.

## 자동 스모크가 확인하는 것 / 확인하지 않는 것

`--smoke` 는 다음만 결정적으로 확인한다:
- 마운트: `[contenteditable]` 요소가 DOM 에 존재하는가, `mountEditor` 컨트롤러
  (`window.__editorCtrl`)가 만들어졌는가.
- 브리지 왕복: JS 에서 `window.pywebview.api.save_chapter(...)` 를 호출해 Python
  쪽 `Api.save_chapter` 가 실제로 실행되고(`spike_data/chapter.html` 생성), 그 반환값이
  JS 로 되돌아오는가.

IME 조합 자체(자모 결합·타이밍·커서 이동)는 **사람 손으로만** 확인 가능하다 —
헤드리스로 키 이벤트를 흉내내는 건 실제 OS IME 엔진 경로를 타지 않아 스파이크의
목적(WKWebView 실환경 검증)과 어긋난다. 그래서 자동화하지 않았다.

## 브리지 비동기 관련 메모

`window.pywebview.api.save_chapter(html)` 는 JS 쪽에서 **Promise** 를 반환하고, 실제
Python 메서드는 별도 스레드에서 실행된다(pywebview `util.js_bridge_call`). `app.py`
의 스모크는 이 때문에 `evaluate_js` 로 Promise 를 즉시 동기 확인하지 않고, JS 쪽에
완료 플래그(`window.__bridgeDone`/`__bridgeResult`)를 심어 폴링한다 — 그렇지 않으면
Python 처리가 끝나기 전에 확인해버리는 레이스가 생긴다(최초 구현에서 실제로 겪음:
`chapter_file_exists: false` 오탐).
