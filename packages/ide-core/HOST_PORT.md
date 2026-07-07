# IDE Host Port v0

"웹뷰 앱은 하나, 호스트는 둘"(dc-73539bba) — `packages/ide-core` 는 데스크탑(pywebview)과
모바일(RN WebView, P2)에 동일 번들로 탑재된다. 이 문서는 웹뷰 앱과 호스트가 주고받는
계약의 **단일 기준**이다. Python(`desktop/app.py`/`desktop/store.py`)과 향후 RN 구현은
반드시 이 계약을 따른다 — 계약이 갈리면(drift) 웹뷰 앱 코드가 한쪽에서만 깨진다.

## 구도

```
packages/ide-core (JS, 순수 — 챕터 사이드바 + mountEditor + host.js 클라이언트)
        │  Host Port (아래 7개 메서드)
        ├── pywebview 어댑터 (v0, 구현됨) → desktop/app.py Api → desktop/store.py (SQLite)
        └── RN postMessage 어댑터 (P2, 미구현)
```

`packages/ide-core/src/host.js` 의 `createHost()` 가 JS 쪽 진입점. v0 는
`createPywebviewHost()` 하나만 구현하고, `window.pywebview.api.*`(snake_case, Python
관례)를 아래 camelCase 계약으로 감싼다.

## 네이밍 규칙

- 브리지 JSON 필드는 **camelCase**. `_cd` 접미어는 노출 전 벗긴다(`status_cd` 컬럼 →
  `status` 필드). `_no`/`orderNo` 는 아예 노출하지 않는다 — 순서는 **배열 순서 자체**로
  표현한다(`listChapters()`/`reorderChapters(ids)` 모두 배열 순서 = 정본 순서).
- id 는 정수(SQLite `INTEGER PRIMARY KEY AUTOINCREMENT`). 브리지를 넘을 때 JS 숫자로
  그대로 전달된다.
- 상태(`status`) 값은 문자열 열거: `"DRAFT" | "REVISING" | "DONE"`. 순환 순서는 이
  순서 그대로(DONE 다음은 다시 DRAFT) — `packages/ide-core/src/chapterOrder.js` 의
  `nextStatus()` 가 정본 구현.

## 계약 (8 메서드 + 발행 3종, P1 슬라이스4)

### `getBook() → {id, title}`

현재 v0 는 책 1권 고정(다중 책 선택 UI 없음) — 항상 가장 먼저 생성된 book 을 반환한다.

```json
// 요청: 없음
// 응답
{ "id": 1, "title": "제목 없는 책" }
```

### `listChapters() → [{id, title, synopsis, status, html?}]`

`order_no` ASC 순 — **배열 순서가 정본 순서**. 사이드바 렌더링용이라 본문(`html`)은
싣지 않는다(가벼움 유지). 전체 본문이 필요하면 `loadChapter(id)`.

```json
// 응답
[
  { "id": 1, "title": "1장", "synopsis": "발단", "status": "DRAFT" },
  { "id": 2, "title": "2장", "synopsis": "", "status": "REVISING" }
]
```

### `loadChapter(id) → {id, title, synopsis, status, html}`

챕터 선택(전환) 시 호출 — 에디터에 넣을 정본 `html`(`<article data-juldoc="1">` 래퍼
포함)을 포함한 전체 레코드.

```json
// 요청
{ "id": 1 }
// 응답
{
  "id": 1,
  "title": "1장",
  "synopsis": "발단",
  "status": "DRAFT",
  "html": "<article data-juldoc=\"1\">\n  <p>본문…</p>\n</article>"
}
```

### `saveChapter(id, {title?, synopsis?, status?, html?}) → {savedAt}`

부분 업데이트 — patch 에 담긴 필드만 갱신, 나머지는 보존. `html` 을 담아 보낼 때는
`mountEditor` 의 `serializeCanonical()` 결과(래퍼 포함 outerHTML)를 그대로 전달한다.
`savedAt` 은 ISO 형식 문자열(`YYYY-MM-DDTHH:MM:SS`).

```json
// 요청
{ "id": 1, "patch": { "html": "<article data-juldoc=\"1\"><p>수정본</p></article>" } }
// 응답
{ "savedAt": "2026-07-08T10:15:00" }
```

### `createChapter({title}) → {id}`

새 챕터를 챕터 목록 맨 끝에 추가(`order_no` = 현재 최대값+1). 초기 `synopsis` = `""`,
`status` = `"DRAFT"`, `html` = 빈 `<article data-juldoc="1">` 래퍼.

```json
// 요청
{ "title": "3장" }
// 응답
{ "id": 3 }
```

### `deleteChapter(id) → {ok}`

멱등 — 존재하지 않는 id 를 넘겨도 `{ok: true}`(에러로 취급하지 않음).

```json
// 요청
{ "id": 2 }
// 응답
{ "ok": true }
```

### `reorderChapters(ids) → {ok}`

챕터 사이드바 드래그 재배열 결과 — **book 의 전체 챕터 id 를 새 순서로 담은 배열**을
그대로 넘긴다(부분 배열 아님). 서버는 `enumerate(ids)` 를 `order_no` 로 기록한다.

```json
// 요청
{ "ids": [3, 1, 2] }
// 응답
{ "ok": true }
```

### `importFile() → {importedCount, chapterIds} | {cancelled: true}`

원고 가져오기(P1 슬라이스3, TXT/MD/DOCX/HWP/HWPX) — 호스트가 OPEN 파일 다이얼로그를
띄우고, 선택된 파일을 `backend/src/engine/doc` 파서로 파싱해 h1 경계로 챕터를 분리한 뒤
**현재 book 의 기존 챕터 뒤에** 순서를 이어 붙인다. 사용자가 다이얼로그를 취소하면
`{cancelled: true}`. `chapterIds` 는 삽입된 순서 그대로(첫 원소 = 원고 첫 챕터) — 호출
측(사이드바)이 보통 `chapterIds[0]` 으로 전환해 방금 가져온 내용을 바로 보여준다.

```json
// 요청: 없음
// 응답(성공)
{ "importedCount": 2, "chapterIds": [4, 5] }
// 응답(취소)
{ "cancelled": true }
```

### `getSettings() → {apiBase, token, hasToken}`

발행(P1 슬라이스4) 설정 조회. `token` 은 마스킹된 값(끝 4자만, 예: `"****ab12"`)이다 —
그대로 다시 `saveSettings()` 에 넣을 값이 아니라 "지금 뭐가 설정돼 있나" 표시용. 저장된
적 없는 필드는 `null`. `hasToken` 으로 토큰 저장 여부를 명확히 구분한다(마스킹 문자열만
보고는 애매해서).

```json
// 응답
{ "apiBase": "http://127.0.0.1:28000", "token": "****ab12", "hasToken": true }
```

### `saveSettings({apiBase?, token?}) → {ok}`

부분 업데이트 — patch 에 담긴 필드만 갱신. 새 토큰은 항상 평문 그대로 여기로 입력받는다
(`getSettings()` 의 마스킹된 값을 그대로 되돌려 넣으면 안 됨).

```json
// 요청
{ "apiBase": "http://127.0.0.1:28000", "token": "eyJhbGciOi..." }
// 응답
{ "ok": true }
```

### `publish() → PublishResult`

로컬 책 전체(모든 챕터)를 `getSettings()` 로 저장된 서버로 밀어넣고 즉시출판한다
(desktop/publisher.py 가 정본 — 서버 계약(book 생성/`PUT content`/`publish-now`)과
클라이언트 프리플라이트(`validate_block_html` 재사용) 상세는 그 모듈 docstring 참고).
책이 아직 서버에 없으면(로컬에 `remote_book_id` 없음) 먼저 생성 후 저장 — 두 번째
발행부터는 같은 원격 책을 갱신(재발행)한다.

프리플라이트 위반(표/이미지/목록/코드 블록, H4 이상 헤딩, `<u>`/링크 등 서버가 모르는
서식)이 있으면 **네트워크 호출 없이** 즉시 실패를 돌려준다 — 부분 발행 없음.

```json
// 응답(성공)
{ "ok": true, "remoteBookId": "b3f1...-uuid", "chapterCount": 3 }
// 응답(프리플라이트 위반 — 발행 안 됨)
{
  "ok": false,
  "violations": [
    { "chapterTitle": "2장", "blockIndex": 4, "blockType": "TABLE", "reason": "알 수 없는 블록 타입: 'TABLE'" }
  ]
}
// 응답(서버 에러 — 예: 가격 미설정)
{ "ok": false, "error": { "status": 422, "message": "출판하려면 가격을 먼저 설정해야 해요." } }
```

## 양쪽 구현 시 지킬 것

- **Python(`desktop/app.py`/`store.py`, 구현됨)**: `js_api` 메서드명은 Python 관례상
  snake_case(`get_book`, `list_chapters`, …, `import_file`, `get_settings`,
  `save_settings`, `publish`) — `host.js` 의 pywebview 어댑터가 이를 camelCase 계약으로
  매핑한다. 반환 dict 의 필드명 자체는 이미 이 문서의 camelCase 규칙을 따른다
  (`status_cd` 컬럼 → `"status"` 키).
- **RN(P2, 미구현)**: `window.ReactNativeWebView.postMessage(...)` + 이벤트 리스너로
  요청/응답을 상관시키는 방식이 유력(pywebview 처럼 직접 함수 호출이 아니므로
  request id 상관관계 필요) — `host.js` 에 `createRNHost()` 를 추가하고
  `createHost({kind:'rn'})` 분기를 늘린다. **이 문서의 8개 메서드 시그니처는
  그대로 유지** — 이중구현 drift 를 이 계약 하나로 가드한다.
- 새 필드를 추가할 때도 이 규칙(camelCase, `_cd`/`_no` 비노출)을 유지하고 이 문서를
  함께 갱신한다.
