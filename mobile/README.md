# 한줄 IDE — P0 스파이크 ⓑ

목적: **iPad(iOS WKWebView, RN `react-native-webview` 내부 엔진)에서 한글 IME 입력이
정상인가**를 사람이 Expo Go 로 직접 확인할 수 있는 최소 실행물. `packages/doc`(한줄독
코어)의 `mountEditor` contenteditable 에디터를 RN WebView 안에 그대로 띄우고,
JS↔React Native `postMessage` 브리지(자동저장) 왕복을 확인한다.

데스크탑 스파이크(`desktop/`, ⓐ — pywebview/macOS WKWebView)와 같은 에디터 코어를
쓴다. macOS와 iOS 는 둘 다 WebKit 이므로, 두 스파이크가 "공유 웹뷰 코어" 전제를
검증하는 짝이다.

이 디렉터리는 루트 npm workspaces(`packages/*`, `web`, `potato`)에 편입되지 않은
독립 프로젝트다. 루트 `package.json`/lockfile 은 건드리지 않는다(`mobile/` 은
`packages/*` glob 밖이라 자체 `node_modules` 로 격리됨).

## 구조

- `mobile/` — Expo(RN) 앱 루트(`create-expo-app --template blank`, **JS**, TypeScript
  아님 — 이 레포 컨벤션).
- `mobile/webapp-spike/` — 빌드 전용 미니 vite 프로젝트. `packages/doc/src/editor.js` 의
  `mountEditor(el, opts)` 를 상대경로로 직접 import(워크스페이스 편입 없이, `desktop/webapp`
  과 동일 패턴). `vite-plugin-singlefile` 로 CSS/JS 를 전부 인라인한 단일 `editor.html` 을
  `dist/`에 낸다 — RN `<WebView source={{ html }}>` 는 문자열 하나로 페이지를 주입하므로
  외부 `<script src>`/`<link href>` 가 하나라도 남으면 파일시스템 baseURL 이 없어 깨진다.
- `mobile/webapp-spike/scripts/emit-module.mjs` — `dist/editor.html` 을 읽어 (1) 외부
  asset 참조가 0건인지 검증하고 (2) `mobile/src/editorHtml.js`(`export const EDITOR_HTML
  = "...";`, JSON.stringify 로 안전 이스케이프)로 변환한다.
- `mobile/src/editorHtml.js` — 위 빌드의 산출물. **AUTO-GENERATED, 직접 수정 금지** —
  커밋은 되어 있지만(바로 `expo start` 가능하도록) `packages/doc` 나 `webapp-spike/src/main.js`
  를 고치면 아래 "에디터 번들 재생성"으로 다시 만들어야 한다.
- `mobile/App.js` — WebView 로드 + postMessage 브리지(저장) + 네이티브 상태 표시.

## 준비

```bash
cd mobile
npm install                 # Expo + react-native-webview + expo-file-system
npm run build:editor        # webapp-spike 빌드 → dist/editor.html → src/editorHtml.js
```

(`packages/doc` 소스나 `webapp-spike/src/main.js` 를 고쳤을 때만 `build:editor` 재실행
필요. `webapp-spike/`는 별도 `node_modules` 라 최초 1회 `npm --prefix webapp-spike install`
도 필요하면 실행 — `npm run build:editor` 가 이미 install 된 상태를 가정.)

## 실행 (사용자가 iPad 에서 직접 확인)

```bash
cd mobile
npx expo start
```

터미널에 뜨는 QR 코드를 iPad 의 **Expo Go** 앱(App Store)으로 스캔 — 같은 Wi-Fi
네트워크에 있어야 한다. 또는 macOS 라면:

```bash
npx expo start --ios   # iOS 시뮬레이터(Xcode 설치 필요) — Expo Go 가 자동 설치/실행됨
```

앱이 뜨면 화면 상단(네이티브 RN 뷰)에 상태 바가, 그 아래 WebView 안에 에디터가
보인다. 에디터 영역을 탭해 키보드를 띄우고 아래 체크리스트를 수행한다.

## 한글 IME 수동 체크리스트 (WebView 에디터 안에서)

에디터 영역을 탭해 포커스를 준 뒤 아래를 순서대로 확인하고, 이상 있으면 정확히
어떤 단계에서 어떻게 깨졌는지 기록한다(가능하면 화면 녹화).

1. **조합 입력** — "안녕하세요"를 타이핑. 자모가 정상적으로 결합되는가(ㅇ+ㅏ+ㄴ→안
   처럼 중간 조합 상태가 자연스럽게 넘어가는가), 완성형이 아닌 낱자모가 남지 않는가.
2. **빠른 연타** — 손이 가는 대로 빠르게 문단 하나를 타이핑. 글자 깨짐·중복 입력·
   순서 뒤바뀜이 없는가.
3. **조합 중 백스페이스** — 자모를 조합하는 도중(예: "가" 입력 중 "ㄱㅏ" 상태)
   백스페이스로 지운다. 조합 중이던 글자가 깨끗이 지워지는가, 커서 위치가 튀지
   않는가.
4. **조합 중 다른 위치 클릭(탭)** — 한글 조합 중(완성되지 않은 상태)에 손가락으로
   문서의 다른 위치를 탭. 조합 중이던 글자가 유실되거나 잘못된 위치에 커밋되지
   않는가.
5. **긴 문단 붙여넣기** — 다른 곳(메모 앱 등)에서 복사한 긴 한글 문단을 붙여넣기.
   방언 정규화(`dialect.js`)를 거쳐 삽입되는데, 한글 텍스트 자체가 깨지지 않는가.
6. **서식 후 이어서 입력** — 툴바에서 굵게(B)/기울임(I)을 누른 뒤 바로 이어서 한글을
   입력. 서식 토글 직후에도 IME 조합이 정상 동작하는가(포커스/커서 유실 없는가).

## 외장 키보드(iPad) 추가 체크

소프트웨어 키보드와 별개로, iPad + 외장 키보드(Magic Keyboard/블루투스) 조합은 IME
경로가 다를 수 있어 별도 확인이 필요하다.

7. **외장 키보드 한/영 전환** — 외장 키보드의 지구본/한영 키(또는 iOS 설정에 등록한
   전환 단축키)로 한/영 전환 후 타이핑. 소프트웨어 키보드와 동일하게 조합되는가.
8. **외장 키보드 빠른 연타 + 백스페이스 조합** — 하드웨어 키 반복입력(키를 누르고
   있을 때 자동반복)이 걸린 상태에서 백스페이스. 소프트웨어 키보드의 2번/3번 항목과
   달리 반복입력 이벤트 처리 경로라 별도로 깨질 수 있다.
9. **외장 키보드에서 소프트웨어 키보드로 전환** — 외장 키보드를 잠깐 뗐다가(또는
   화면 상단에서 소프트웨어 키보드 토글) 다시 소프트웨어 키보드로 전환 후 조합 중이던
   상태가 유지/유실되는지.

## 저장/브리지 확인

에디터에 입력하면 2초 디바운스 뒤 자동저장이 실행된다(또는 `mountEditor` 의 `save()`
가 명시 호출될 때). 흐름:

1. 웹 페이지(`webapp-spike/src/main.js`)가
   `window.ReactNativeWebView.postMessage(JSON.stringify({type:'save', saveId, html}))` 전송.
2. `App.js` 의 `onMessage` 가 받아 `expo-file-system` 으로
   `FileSystem.documentDirectory + 'hanjul-ide-spike-editor.html'` 에 기록.
3. 기록이 끝난 **뒤에** `injectJavaScript` 로 웹 페이지의
   `window.__onSaveResult(saveId, ok, meta)` 를 호출 — 웹 쪽 저장 Promise 는 이 콜백이
   올 때까지 대기한다(postMessage 를 보냈다고 저장이 끝났다고 가정하지 않는다 — P0 ⓐ
   에서 겪은 "동기 반환 신뢰 금지" 교훈을 여기서도 지킨다. 타임아웃 8초 안전장치 포함).

화면에서 확인 가능한 것:
- WebView 상단 상태바(`저장 상태: ...`) — `편집 중… → 저장 중… → 저장됨 · HH:MM:SS
  (N chars, RN)`.
- 네이티브 RN 상태바(화면 최상단) — `네이티브 저장 완료 · HH:MM:SS (N chars)` + 파일
  경로, `브리지 메시지 수신: N회` 카운터(탭할 때마다 증가하면 왕복이 실제로 일어나는
  증거).

## 알려진 한계 / 미해결 (사용자 몫)

- **실기기 IME 검증은 자동화하지 않았다** — 헤드리스로 키 이벤트를 흉내내는 건 실제
  OS IME 엔진 경로를 타지 않아 스파이크 목적(WKWebView 실환경 검증)과 어긋난다
  (데스크탑 ⓐ 와 동일 판단). 위 체크리스트는 사람이 iPad 에서 직접 수행해야 한다.
- **Expo Go 에서 안 되는 것**: 네이티브 모듈을 추가로 링크해야 하는 기능(예: 커스텀
  네이티브 코드가 필요한 파일 피커 등)은 Expo Go 에서 동작하지 않는다. 이 스파이크가
  쓰는 `react-native-webview`/`expo-file-system` 은 Expo Go 에 기본 포함된 SDK라 QR
  스캔만으로 동작해야 한다 — 만약 Expo Go 에서 모듈을 못 찾는다는 에러가 뜨면 Expo
  SDK 버전 불일치(Expo Go 앱 업데이트 필요)를 의심할 것.
- **재시작 시 이전 저장 내용 복원 안 함** — 이 스파이크는 IME/브리지 검증이 목적이라
  앱을 껐다 켜면 항상 초기 샘플 텍스트로 돌아간다(파일에는 계속 기록되지만 시작 시
  읽어오지 않음). 실제 저장 파일(`hanjul-ide-spike-editor.html`)이 갱신되는지는
  `expo-file-system` 의 `getInfoAsync`/기기 파일 앱(Files → On My iPad → Expo Go 아래
  샌드박스는 직접 안 보임 — 필요하면 `App.js` 에 디버그용 읽기 버튼을 추가해 확인)로만
  간접 확인 가능.
- **정적 검증만 CI/스크립트로 확인함** — `expo export`/`expo-doctor` 등 정적 빌드
  검증까지만 이 스파이크 구현 시 실행했다. 시뮬레이터/실기기 부팅·실행은 무겁고 환경
  의존적이라 의도적으로 시도하지 않았다 — 위 QR/시뮬레이터 실행부터는 사용자가 직접.
- **Android 는 범위 밖** — 목적이 "iPad WKWebView" 검증이라 Android WebView(Chromium
  기반, 다른 IME 경로)는 이 스파이크의 관심사가 아니다. 다만 코드 자체는
  `react-native-webview` 표준 API 만 쓰므로 Android 에서도 그대로 뜨긴 할 것이다
  (검증 안 함).

## 에디터 번들 재생성 (packages/doc 을 고쳤을 때)

```bash
cd mobile
npm run build:editor
```

내부적으로 `webapp-spike` 에서 `vite build`(→ `dist/editor.html`) 후
`scripts/emit-module.mjs`(→ `../src/editorHtml.js`, 단일파일 검증 포함) 를 순서대로
실행한다. 검증 실패(외부 asset 참조 잔존) 시 non-zero exit + 어떤 참조가 남았는지
콘솔에 출력하고 `editorHtml.js` 를 갱신하지 않는다.
