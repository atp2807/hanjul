// host.js — IDE Host Port v0 클라이언트. 웹뷰 앱(ide-core)이 호스트(PyWebView/RN)와
// 통신하는 유일한 통로. 계약 전문은 ../HOST_PORT.md 참고.
//
// 인터페이스는 플랫폼 중립(HostPort 의 7개 메서드는 pywebview/RN 어디서든 동일) —
// v0 는 pywebview 어댑터만 구현한다. RN WebView 호스트가 붙으면 postMessage 기반
// 어댑터를 이 파일에 추가하고 createHost() 분기만 늘리면 된다
// (dc-73539bba "웹뷰 앱은 하나, 호스트는 둘").
//
// 주의(lr-9a45e6e4): pywebview 의 evaluate_js 는 Promise 를 동기적으로 풀 수 없어
// Python 쪽(desktop/app.py)의 스모크 테스트가 완료 플래그 폴링을 쓴다 — 그건
// "브라우저 콘솔에서 evaluate_js 로 비동기 결과를 훔쳐볼 때"의 문제다. 여기 JS 쪽에서
// window.pywebview.api.xxx(...) 를 직접 await 하는 건 pywebview 가 제공하는 정상
// Promise 경로이므로 해당 없음 — 그대로 await 하면 된다.

const READY_TIMEOUT_MS = 5000;

function hasPywebviewApi() {
  return typeof window !== 'undefined' && typeof window.pywebview?.api?.get_book === 'function';
}

/** pywebview 는 페이지 로드 후 비동기로 api 를 주입한다 — 준비될 때까지 대기. */
function waitForPywebview(timeoutMs = READY_TIMEOUT_MS) {
  if (hasPywebviewApi()) return Promise.resolve();
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      window.removeEventListener('pywebviewready', onReady);
      reject(new Error('host.js: pywebview 브리지 준비 타임아웃'));
    }, timeoutMs);
    function onReady() {
      clearTimeout(timer);
      resolve();
    }
    window.addEventListener('pywebviewready', onReady, { once: true });
    // 리스너 등록 사이 이미 준비됐을 수 있으니 한 번 더 확인(레이스 방지).
    if (hasPywebviewApi()) onReady();
  });
}

/**
 * @typedef {Object} ChapterSummary
 * @property {number} id
 * @property {string} title
 * @property {string} synopsis
 * @property {string} status
 * @property {string} [html]
 *
 * @typedef {Object} HostPort
 * @property {() => Promise<{id:number, title:string}>} getBook
 * @property {() => Promise<ChapterSummary[]>} listChapters
 * @property {(id:number) => Promise<ChapterSummary & {html:string}>} loadChapter
 * @property {(id:number, patch:{title?:string, synopsis?:string, status?:string, html?:string}) => Promise<{savedAt:string}>} saveChapter
 * @property {(opts:{title:string}) => Promise<{id:number}>} createChapter
 * @property {(id:number) => Promise<{ok:boolean}>} deleteChapter
 * @property {(ids:number[]) => Promise<{ok:boolean}>} reorderChapters
 * @property {() => Promise<{importedCount:number, chapterIds:number[]} | {cancelled:true}>} importFile
 * @property {() => Promise<{apiBase:string|null, token:string|null, hasToken:boolean}>} getSettings
 * @property {(settings:{apiBase?:string, token?:string}) => Promise<{ok:boolean}>} saveSettings
 * @property {() => Promise<PublishResult>} publish
 */

/**
 * @typedef {Object} PublishViolation
 * @property {string} chapterTitle
 * @property {number} blockIndex
 * @property {string} blockType
 * @property {string} reason
 *
 * @typedef {Object} PublishResult
 * @property {boolean} ok
 * @property {string} [remoteBookId]
 * @property {number} [chapterCount]
 * @property {PublishViolation[]} [violations]
 * @property {{status:number|null, message:string}} [error]
 */

/**
 * v0 pywebview 어댑터 — window.pywebview.api.*(snake_case, desktop/app.py 계약)를
 * Host Port 계약(camelCase)으로 감싼다.
 * @returns {HostPort}
 */
export function createPywebviewHost() {
  async function api() {
    await waitForPywebview();
    return window.pywebview.api;
  }
  return {
    async getBook() {
      return (await api()).get_book();
    },
    async listChapters() {
      return (await api()).list_chapters();
    },
    async loadChapter(id) {
      return (await api()).load_chapter(id);
    },
    async saveChapter(id, patch) {
      return (await api()).save_chapter(id, patch || {});
    },
    async createChapter({ title }) {
      return (await api()).create_chapter(title);
    },
    async deleteChapter(id) {
      return (await api()).delete_chapter(id);
    },
    async reorderChapters(ids) {
      return (await api()).reorder_chapters(ids);
    },
    async importFile() {
      return (await api()).import_file();
    },
    async getSettings() {
      return (await api()).get_settings();
    },
    async saveSettings(settings) {
      return (await api()).save_settings(settings || {});
    },
    async publish() {
      return (await api()).publish();
    },
  };
}

/**
 * 호스트 팩토리 — v0 는 'pywebview' 만 지원한다. RN 어댑터가 생기면 kind 분기를 늘린다.
 * @param {{kind?: 'pywebview'}} [opts]
 * @returns {HostPort}
 */
export function createHost({ kind = 'pywebview' } = {}) {
  if (kind === 'pywebview') return createPywebviewHost();
  throw new Error(`host.js: 지원하지 않는 호스트 종류 "${kind}" (v0는 pywebview만 구현)`);
}
