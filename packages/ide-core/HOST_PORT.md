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

## 계약 (7 메서드)

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

## 양쪽 구현 시 지킬 것

- **Python(`desktop/app.py`/`store.py`, 구현됨)**: `js_api` 메서드명은 Python 관례상
  snake_case(`get_book`, `list_chapters`, …) — `host.js` 의 pywebview 어댑터가 이를
  camelCase 계약으로 매핑한다. 반환 dict 의 필드명 자체는 이미 이 문서의 camelCase
  규칙을 따른다(`status_cd` 컬럼 → `"status"` 키).
- **RN(P2, 미구현)**: `window.ReactNativeWebView.postMessage(...)` + 이벤트 리스너로
  요청/응답을 상관시키는 방식이 유력(pywebview 처럼 직접 함수 호출이 아니므로
  request id 상관관계 필요) — `host.js` 에 `createRNHost()` 를 추가하고
  `createHost({kind:'rn'})` 분기를 늘린다. **이 문서의 7개 메서드 시그니처는
  그대로 유지** — 이중구현 drift 를 이 계약 하나로 가드한다.
- 새 필드를 추가할 때도 이 규칙(camelCase, `_cd`/`_no` 비노출)을 유지하고 이 문서를
  함께 갱신한다.
