// 한줄 IDE 모바일 스파이크(ⓑ) — packages/doc 의 mountEditor(el, opts) 를 RN WebView 안에서
// 그대로 사용한다. 데스크탑 스파이크(desktop/webapp/src/main.js)와 같은 코어, 셸 브리지만
// pywebview → React Native postMessage 로 교체.
//
// 시그니처(packages/doc/src/editor.js:144): mountEditor(el, {html, onSave, onDirty, onStatus, ...})
// -> {save, isDirty, getHtml, ..., destroy}. 마운트 대상 html 은 반드시
// <article data-juldoc="1"> 래퍼를 포함해야 한다(없으면 editor.js:149-151 에서 throw).
//
// RN 브리지 왕복 (P0 ⓐ 교훈 — 동기 반환을 신뢰하지 않는다):
//  1) 저장 시 window.ReactNativeWebView.postMessage(JSON.stringify({type:'save', saveId, html})).
//     postMessage 는 "보냈다"만 보장 — RN 이 실제로 파일을 썼는지는 알 수 없다.
//  2) RN(App.js)이 expo-file-system 기록을 마친 뒤 injectJavaScript 로 이 페이지의
//     window.__onSaveResult(saveId, ok, meta) 를 호출해야 비로소 onSave() 의 Promise 가
//     resolve/reject 된다. 그 전까지는 pendingSaves 맵에 대기.
//  3) RN 이 죽거나 응답을 안 주는 경우를 대비해 타임아웃으로 reject(무한 대기 금지).
import { mountEditor } from '../../../packages/doc/src/editor.js';
import '../../../packages/doc/src/doc.css';

const SAMPLE_HTML = `<article data-juldoc="1">
  <h1>한줄 IDE 모바일 스파이크</h1>
  <p>여기에 한글을 입력해 IME 조합(자모 결합)이 정상인지 확인하세요.</p>
  <p>예: 안녕하세요, 반갑습니다. 빠르게 연타해도 자모가 깨지지 않는지 확인.</p>
</article>`;

const SAVE_TIMEOUT_MS = 8000;

const statusEl = document.getElementById('status');
const editorEl = document.getElementById('editor');

function setStatus(text) {
  statusEl.textContent = text;
}

function hasBridge() {
  return typeof window.ReactNativeWebView?.postMessage === 'function';
}

let saveCounter = 0;
/** @type {Map<number, {resolve:(v:any)=>void, reject:(e:Error)=>void, timer:ReturnType<typeof setTimeout>}>} */
const pendingSaves = new Map();

/** RN 이 injectJavaScript 로 호출하는 콜백 — 페이지 전역(window)에 노출해야 RN 쪽에서 부를 수 있다. */
window.__onSaveResult = function onSaveResult(saveId, ok, meta) {
  const pending = pendingSaves.get(saveId);
  if (!pending) return; // 이미 타임아웃되었거나 모르는 saveId — 조용히 무시.
  pendingSaves.delete(saveId);
  clearTimeout(pending.timer);
  if (ok) pending.resolve(meta || {});
  else pending.reject(new Error(meta?.error || '저장 실패(RN)'));
};

function requestSave(html) {
  if (!hasBridge()) {
    return Promise.reject(new Error('ReactNativeWebView.postMessage 없음 (WebView 밖 실행 중?)'));
  }
  const saveId = ++saveCounter;
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      pendingSaves.delete(saveId);
      reject(new Error('저장 타임아웃 — RN 응답 없음'));
    }, SAVE_TIMEOUT_MS);
    pendingSaves.set(saveId, { resolve, reject, timer });
    window.ReactNativeWebView.postMessage(JSON.stringify({ type: 'save', saveId, html }));
  });
}

const ctrl = mountEditor(editorEl, {
  html: SAMPLE_HTML,
  onSave: async (html) => {
    const result = await requestSave(html);
    setStatus(`저장됨 · ${result.savedAt || ''} (${result.bytes ?? '?'} chars, RN)`);
    return result;
  },
  onDirty: (dirty) => {
    if (dirty) setStatus('편집 중… (자동저장 대기 2초)');
  },
  onStatus: (state, err) => {
    if (state === 'saving') setStatus('저장 중… (RN 응답 대기)');
    if (state === 'error') setStatus(`저장 실패: ${err?.message || err}`);
  },
});

// 스모크/디버그 훅 — WebView.injectJavaScript 로 상태를 evaluate 할 때 쓸 수 있게.
window.__editorCtrl = ctrl;

setStatus(hasBridge() ? '대기 중 (RN 브리지 연결됨)' : '대기 중 (브리지 없음 — WebView 밖 실행?)');
