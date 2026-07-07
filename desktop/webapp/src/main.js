// 한줄 IDE P0 스파이크 — packages/doc 의 mountEditor(el, opts) 를 그대로 사용한다.
// 시그니처(packages/doc/src/editor.js:144): mountEditor(el, {html, onSave, onDirty,
// onStatus, onUploadMedia, apiBase}) -> {save, isDirty, getHtml, ..., destroy}.
// 마운트 대상 html 은 반드시 <article data-juldoc="1"> 래퍼를 포함해야 한다
// (없으면 editor.js:149-151 에서 throw).
import { mountEditor } from '../../../packages/doc/src/editor.js';
import '../../../packages/doc/src/doc.css';

const SAMPLE_HTML = `<article data-juldoc="1">
  <h1>한줄 IDE 스파이크</h1>
  <p>여기에 한글을 입력해 IME 조합(자모 결합)이 정상인지 확인하세요.</p>
  <p>예: 안녕하세요, 반갑습니다.</p>
</article>`;

const statusEl = document.getElementById('status');
const editorEl = document.getElementById('editor');

function setStatus(text) {
  statusEl.textContent = text;
}

function hasBridge() {
  return typeof window.pywebview?.api?.save_chapter === 'function';
}

const ctrl = mountEditor(editorEl, {
  html: SAMPLE_HTML,
  onSave: async (html) => {
    if (!hasBridge()) {
      // pywebview 브리지 준비 전(또는 브라우저 단독 실행) — 콘솔에만 남기고 저장 실패로 처리.
      setStatus('저장 실패: pywebview.api 없음 (셸 밖 실행 중?)');
      throw new Error('pywebview.api.save_chapter unavailable');
    }
    const result = await window.pywebview.api.save_chapter(html);
    setStatus(`저장됨 · ${result.saved_at} (${result.bytes} bytes)`);
    return result;
  },
  onDirty: (dirty) => {
    if (dirty) setStatus('편집 중… (자동저장 대기 2초)');
  },
  onStatus: (state, err) => {
    if (state === 'saving') setStatus('저장 중…');
    if (state === 'error') setStatus(`저장 실패: ${err?.message || err}`);
  },
});

// 스모크 테스트(app.py --smoke)가 evaluate_js 로 브리지 왕복을 확인할 때 쓰는 훅.
window.__editorCtrl = ctrl;

// pywebview 브리지가 페이지 로드 후 비동기로 주입되므로 준비 상태를 상태바에 반영.
window.addEventListener('pywebviewready', () => setStatus('대기 중 (브리지 연결됨)'));
if (hasBridge()) setStatus('대기 중 (브리지 연결됨)');
