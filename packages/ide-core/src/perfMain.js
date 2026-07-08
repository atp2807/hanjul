// perfMain.js — L0 계측 하네스(dc-81277381). desktop/app.py --perf 가 dist/perf.html 을
// 숨김창(lr-9a45e6e4)으로 로드한 뒤 evaluate_js 로 window.__perfHarness.run() 을 구동한다.
// 완료는 window.__perfDone/__perfResult 플래그 폴링(desktop/app.py:run_smoke 와 동일
// 패턴 — pywebview evaluate_js 가 Promise 를 동기 해석 못 해 값을 놓치는 레이스 회피).
//
// 측정 대상은 packages/doc/src/editor.js 의 mountEditor 그 자체 — ide-core 의 챕터
// 사이드바/호스트 브리지(app.js/host.js)는 개입하지 않는다. L0 은 에디터 코어 성능만
// 본다(dc-81277381 정정사항 참고: content-visibility 는 layout/paint 만 스킵하고 DOM
// construction 은 O(n) 그대로라 "마운트 시간"을 별도로 재는 게 이 하네스의 핵심 목적).
import { mountEditor } from '../../doc/src/editor.js';
import '../../doc/src/doc.css';

// 합성 챕터 3종 — 목표는 "태그 제외 텍스트 길이" 기준 1만/3만/10만 자(dc-81277381 L0 예산).
const SYNTHETIC_SIZES = { size_1man: 10000, size_3man: 30000, size_10man: 100000 };
const INPUT_LATENCY_N = 50;
const SCROLL_DURATION_MS = 1000;

const SENTENCE = '문단 본문 텍스트입니다. 성능 계측용 합성 데이터이며 실제 원고 내용은 아닙니다. ';

/**
 * 평평한 정본 HTML 생성 — p 문단 다수 + h1/h2 섞기, <article data-juldoc="1"> 래퍼.
 * targetChars 는 마크업 제외 텍스트 길이 기준(약간 초과할 수 있음).
 * @param {number} targetChars
 * @returns {string}
 */
function buildSyntheticHtml(targetChars) {
  const parts = [];
  let total = 0;
  let i = 0;
  while (total < targetChars) {
    i += 1;
    if (i % 20 === 0) {
      const t = `장 ${i / 20}`;
      parts.push(`<h1>${t}</h1>`);
      total += t.length;
    } else if (i % 7 === 0) {
      const t = `절 ${i}`;
      parts.push(`<h2>${t}</h2>`);
      total += t.length;
    } else {
      parts.push(`<p>${SENTENCE}</p>`);
      total += SENTENCE.length;
    }
  }
  return `<article data-juldoc="1">${parts.join('')}</article>`;
}

/** 순수 백분위(선형보간 없음, N 작을 때도 안정적인 nearest-rank). */
function percentile(values, p) {
  const sorted = [...values].sort((a, b) => a - b);
  const idx = Math.min(sorted.length - 1, Math.max(0, Math.ceil((p / 100) * sorted.length) - 1));
  return sorted[idx];
}

/** 이 WebView 가 content-visibility 를 지원하는지 — 미지원이면 c-v 델타 0 이 정상. */
function supportsContentVisibility() {
  return (
    typeof CSS !== 'undefined' &&
    typeof CSS.supports === 'function' &&
    CSS.supports('content-visibility', 'auto')
  );
}

function makeContainer(cvEnabled) {
  const el = document.createElement('div');
  el.id = 'perf-container';
  if (cvEnabled) el.classList.add('cv-on');
  el.style.width = '800px';
  el.style.height = '600px';
  el.style.overflowY = 'auto';
  document.body.appendChild(el);
  return el;
}

/** 1) 마운트 시간 — el.innerHTML=html 반영~레이아웃 완료(강제 리플로우)까지 ms. */
function measureMount(html, cvEnabled) {
  const container = makeContainer(cvEnabled);
  const t0 = performance.now();
  const ctrl = mountEditor(container, { html, onSave: async () => {} });
  void container.offsetHeight; // 강제 리플로우
  const t1 = performance.now();
  return { mountMs: t1 - t0, ctrl, container };
}

/**
 * 2) 직렬화 비용 — article.outerHTML + onSave 경로(L1 타깃 직접 측정).
 *
 * 단일 호출(singleMs, 명세상 "1회")은 WebKit 의 clamp 된 performance.now() 해상도
 * (~1ms 단위, 타이밍 공격 완화용) 아래로 실비용이 깔릴 수 있어 0 으로 뭉개질 수 있다 —
 * 그래서 avgMs(iterations 회 반복의 총 경과시간/반복수, 타임스탬프는 루프 앞뒤 2번만
 * 읽어 clamp 노이즈를 iterations 로 나눠 희석)를 L1 문턱값 판단의 1차 근거로 쓴다.
 */
async function measureSerialize(html, cvEnabled, iterations = 10) {
  const container = makeContainer(cvEnabled);
  const ctrl = mountEditor(container, { html, onSave: async () => {} });
  await ctrl.save(); // 워밍업(최초 레이아웃/JIT 안정화) — 측정 제외

  const s0 = performance.now();
  await ctrl.save(); // 실측 단발 1회: serializeCanonical(article.outerHTML) + onSave 호출
  const s1 = performance.now();
  const singleMs = s1 - s0;

  const t0 = performance.now();
  for (let i = 0; i < iterations; i += 1) {
    await ctrl.save(); // 의도적 순차 반복(평균 비용 측정)
  }
  const t1 = performance.now();
  const avgMs = (t1 - t0) / iterations;

  ctrl.destroy();
  container.remove();
  return { singleMs, avgMs, iterations };
}

/**
 * 3) 입력 지연 프록시 — contenteditable 에 프로그램적으로 텍스트 삽입 후 강제
 * 리플로우까지 ms 를 N 회, p50/p95. 주의: 진짜 하드웨어 키입력→페인트가 *아니다* —
 * execCommand('insertText') 삽입 + offsetHeight 강제 리플로우로 근사한 프록시 수치.
 */
function measureInputLatency(html, cvEnabled, n = INPUT_LATENCY_N) {
  const container = makeContainer(cvEnabled);
  const ctrl = mountEditor(container, { html, onSave: async () => {} });
  const article = container.querySelector('article[data-juldoc]');
  article.focus();
  const range = document.createRange();
  range.selectNodeContents(article);
  range.collapse(false);
  const sel = document.getSelection();
  sel.removeAllRanges();
  sel.addRange(range);

  const times = [];
  for (let i = 0; i < n; i += 1) {
    const t0 = performance.now();
    document.execCommand('insertText', false, 'a');
    void article.offsetHeight; // 강제 리플로우
    const t1 = performance.now();
    times.push(t1 - t0);
  }
  ctrl.destroy();
  container.remove();
  return { n, p50: percentile(times, 50), p95: percentile(times, 95) };
}

/**
 * requestAnimationFrame 이 실제로 발화하는지 짧게 프로브한다. 실측 확인(raf_probe 진단,
 * 2026-07-08): 이 하네스는 항상 hidden 창(lr-9a45e6e4, 창 깜빡임 금지)인데, WKWebView 는
 * 화면에 안 보이는(hidden) 창의 컴포지터 스케줄을 완전히 멈춰 rAF 콜백이 *전혀* 오지
 * 않는다(8초 대기해도 0회) — 그래서 rAF 로만 스크롤 fps 를 재면 영원히 멈춘다.
 * @returns {Promise<boolean>}
 */
function probeRaf(timeoutMs = 250) {
  return new Promise((resolve) => {
    let settled = false;
    const timer = setTimeout(() => {
      if (!settled) {
        settled = true;
        resolve(false);
      }
    }, timeoutMs);
    requestAnimationFrame(() => {
      if (!settled) {
        settled = true;
        clearTimeout(timer);
        resolve(true);
      }
    });
  });
}

/**
 * 4) 스크롤 fps — 프로그램적 스크롤 중 프레임 델타로 평균/최저 fps.
 *
 * 명세상 requestAnimationFrame 델타가 정본이지만, 이 하네스는 hidden 창 제약(위 probeRaf
 * 참고) 때문에 rAF 가 실제로 도는지 먼저 확인하고, 안 돌면 setTimeout(16ms) 로 대체한다.
 * **주의**: setTimeout 대체 경로의 fps 는 실제 컴포지터 페인트 주기가 아니라 "스크롤
 * 루프 1회(scrollTop 대입 + 강제 없음)당 JS 이벤트루프 왕복 시간"의 근사치일 뿐이다 —
 * hidden 창에서는애초에 화면에 그려지는 페인트 자체가 없으므로 "진짜 스크롤 fps"는
 * 이 하네스로 원천적으로 측정 불가하다(결과의 rafAvailable:false 가 이 상태를 표시).
 */
async function measureScrollFps(html, cvEnabled, durationMs = SCROLL_DURATION_MS) {
  const container = makeContainer(cvEnabled);
  const ctrl = mountEditor(container, { html, onSave: async () => {} });
  const maxScroll = Math.max(1, container.scrollHeight - container.clientHeight);
  const rafAvailable = await probeRaf();
  const scheduleFrame = rafAvailable
    ? (cb) => requestAnimationFrame(cb)
    : (cb) => setTimeout(() => cb(performance.now()), 16);

  return new Promise((resolve) => {
    const deltas = [];
    let last = null;
    let start = null;
    function step(ts) {
      if (start == null) start = ts;
      if (last != null) deltas.push(ts - last);
      last = ts;
      const elapsed = ts - start;
      container.scrollTop = Math.min(1, elapsed / durationMs) * maxScroll;
      if (elapsed < durationMs) {
        scheduleFrame(step);
        return;
      }
      const fpsSamples = deltas.filter((d) => d > 0).map((d) => 1000 / d);
      const avgFps = fpsSamples.length
        ? fpsSamples.reduce((a, b) => a + b, 0) / fpsSamples.length
        : 0;
      const minFps = fpsSamples.length ? Math.min(...fpsSamples) : 0;
      ctrl.destroy();
      container.remove();
      resolve({ frames: fpsSamples.length, avgFps, minFps, maxScroll, rafAvailable });
    }
    scheduleFrame(step);
  });
}

// 진행상황 — 하네스가 도중에 멎어도(타임아웃) app.py 가 window.__perfProgress 를 읽어
// 어디까지 갔는지 진단할 수 있게 매 단계 뒤에 남긴다(2026-07-08 hidden-rAF 이슈로 한 번
// 실제 행 걸린 뒤 추가한 진단 장치).
window.__perfProgress = [];

async function runOneConfig(sizeLabel, targetChars, cvEnabled) {
  const html = buildSyntheticHtml(targetChars);
  const tag = `${sizeLabel}/cv=${cvEnabled}`;

  const { mountMs, ctrl: mountCtrl, container: mountContainer } = measureMount(html, cvEnabled);
  mountCtrl.destroy();
  mountContainer.remove();
  window.__perfProgress.push(`${tag}:mount`);

  const serialize = await measureSerialize(html, cvEnabled);
  window.__perfProgress.push(`${tag}:serialize`);
  const inputLatency = measureInputLatency(html, cvEnabled);
  window.__perfProgress.push(`${tag}:inputLatency`);
  const scroll = await measureScrollFps(html, cvEnabled);
  window.__perfProgress.push(`${tag}:scroll`);

  return {
    size: sizeLabel,
    targetChars,
    actualChars: html.length, // 참고용(마크업 포함 대략치) — targetChars 가 텍스트 기준 정본
    cvEnabled,
    mountMs,
    serialize,
    inputLatency,
    scroll,
  };
}

async function runAll() {
  const cvSupported = supportsContentVisibility();
  const configs = [];
  const sizeEntries = Object.entries(SYNTHETIC_SIZES);
  for (let s = 0; s < sizeEntries.length; s += 1) {
    const [label, chars] = sizeEntries[s];
    for (let c = 0; c < 2; c += 1) {
      const cvEnabled = c === 1;
      // 하네스는 의도적으로 순차 실행 — 설정 간 간섭(레이아웃/GC) 없는 실측이 목적.
      configs.push(await runOneConfig(label, chars, cvEnabled));
    }
  }
  return {
    userAgent: navigator.userAgent,
    contentVisibilitySupported: cvSupported,
    results: configs,
  };
}

window.__perfHarness = { run: runAll };
const statusEl = document.getElementById('perf-status');
if (statusEl) statusEl.textContent = '하네스 준비 완료';
