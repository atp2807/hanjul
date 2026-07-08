# L0 성능 계측 하네스 (dc-81277381)

한줄 IDE 장문 편집 성능 설계(LinkLore `dc-81277381`)의 L0 레이어 — `packages/doc/src/editor.js`
의 `mountEditor` 자체(챕터 사이드바/호스트 브리지 미개입)를 합성 챕터 3종으로 구동해
마운트/직렬화/입력지연 프록시/스크롤 fps 를 실측하고, content-visibility on/off 비교까지
한 번에 낸다.

## 실행

```bash
# 1) 웹뷰 앱 빌드(최초 1회 또는 packages/ide-core, packages/doc 변경 후) — 저장소 루트에서
npm install
npm run build -w packages/ide-core   # dist/index.html + dist/perf.html 산출

# 2) 하네스 구동 — 항상 숨김창(lr-9a45e6e4, 창 깜빡임 금지)
cd desktop
.venv/bin/python app.py --perf                     # 기본 타임아웃 60초
.venv/bin/python app.py --perf --perf-timeout 120  # 느린 머신 등, 타임아웃 늘리기
```

stdout 에 `PERF_RESULT {...}` JSON 한 줄이 출력되고, 동일 내용이 `desktop/perf/report.json`
(gitignore 대상 — 실행마다 새로 갱신되는 산출물)에도 저장된다.

## 측정 항목 (packages/ide-core/src/perfMain.js)

합성 챕터 3종(1만/3만/10만 자, p 문단 다수 + h1/h2 섞은 평평한 정본 HTML) × content-visibility
on/off 2가지 = 총 6 설정. 설정마다:

1. **mountMs** — `el.innerHTML=html`(mountEditor 내부) 반영부터 강제 리플로우
   (`container.offsetHeight` 읽기)까지. **실측**(진짜 마운트 비용). c-v 는 DOM
   construction 을 스킵 못 하므로(dc-81277381 정정사항 2) c-v on/off 무관하게 비슷해야
   "정상" — 여기서 큰 델타가 보이면 그 자체가 이상신호.
2. **serialize.{singleMs, avgMs, iterations}** — `ctrl.save()`(= `article.outerHTML`
   직렬화 + onSave 경로) 1회(`singleMs`) 및 10회 반복 총 경과/10(`avgMs`). **실측**.
   `singleMs` 는 WebKit 의 clamp 된 `performance.now()` 해상도(~1ms, 타이밍공격 완화용)
   때문에 0 으로 뭉개지기 쉬워 `avgMs` 를 1차 판단 근거로 쓴다. L1(idle 직렬화) 발동
   여부의 직접 게이트.
3. **inputLatency.{n, p50, p95}** — contenteditable 끝에 캐럿을 두고
   `execCommand('insertText')` N=50 회 + 매회 강제 리플로우. **프록시**다 — 진짜
   하드웨어 키 입력→페인트가 아니라 "프로그램적 삽입+강제 리플로우"의 근사치.
4. **scroll.{frames, avgFps, minFps, rafAvailable}** — 프로그램적 스크롤 중 프레임
   델타. **주의(중요, 실측으로 확인된 한계)**: 이 하네스는 항상 숨김창이라
   `requestAnimationFrame` 이 전혀 발화하지 않는다(WKWebView 가 안 보이는 창의
   컴포지터 스케줄을 완전히 멈춤 — 별도 진단 스크립트로 8초 대기해도 0회 확인됨).
   `rafAvailable:false` 면 `setTimeout(16ms)` 폴백으로 대체하지만, **hidden 창의
   백그라운드 타이머 스로틀링** 때문에 이 폴백조차 신뢰 불가 — 실측상 맨 처음 실행되는
   설정(1만자/c-v off)만 우연히 ~47fps 근사치가 나오고, 이후 모든 설정은 스로틀링에
   걸려 `avgFps≈1`(=사실상 무의미)로 수렴한다. **이 하네스로는 "진짜 스크롤 fps"를
   결론 낼 수 없다** — hidden 정책과 정면충돌하는 근본 제약(해결하려면 보이는 창이
   필요한데, 그건 이 하네스의 창 깜빡임 금지 원칙과 상충). 후속 필요 시 별도의,
   자동화 파이프라인 밖 수동 1회성 "보이는 창" 실행으로만 검증 가능.

각 설정은 실행마다 독립적으로 `mountEditor`를 새로 마운트/destroy 한다(단계 간 간섭 방지).

## content-visibility 적용 방식

`perf.html` 의 `<style>` 에 `#perf-container.cv-on article[data-juldoc] > * { content-visibility:
auto; contain-intrinsic-size: auto 120px; }` 를 선언해두고, 컨테이너에 `cv-on` 클래스를
**마운트 전**에 미리 붙인다 — `el.innerHTML=html` 대입 시점부터 이미 스타일이 매칭되게
해서 "이미 c-v 가 걸린 문서를 여는" 실제 시나리오와 최대한 가깝게 만든다(마운트 후
JS 로 후처리 적용하면 그 시나리오와 달라진다).

`contentVisibilitySupported` 필드로 이 WebView 가 `content-visibility: auto` 를
`CSS.supports()` 기준으로 지원하는지 판정한 값을 같이 낸다(미지원이면 on/off 델타가
0에 수렴하는 게 정상).
