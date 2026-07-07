// mountEditor(el, {html, onSave, onDirty, onStatus, onUploadMedia, apiBase}) — contenteditable 흐름 편집기.
//
// 프레임워크 무소속 코어 — DOM 이 곧 문서 상태. React 래퍼(DocEditor.jsx)는 이 모듈을
// ref 에 1회 마운트만 하고 리렌더하지 않는다(내용 = DOM 이 정본).
//
// 결정사항(엄수):
//  1) DOM 이 곧 문서 상태. 서버 정본 <article data-juldoc="1"> 을 그대로 넣고
//     article 에 contenteditable. 별도 내부 모델 없음. 저장 = article.outerHTML PUT.
//  2) 편집은 흐름 모드 — 편집 중 페이지 조판 없음(조판은 reader 몫).
//  3) paste/drop 시 text/html 을 dialect 로 정규화 후 삽입 (UX용; 보안 최종
//     방어선은 서버 parse_dialect 다). drop 도 paste 와 동일 경로 — 우회 금지.
//  4) 자동저장 = 입력 후 2초 디바운스 + 명시 save(). 저장 응답으로 DOM 교체 금지
//     (커서 점프 방지) — dirty 플래그만 해제. 저장 *실패* 시 dirty 유지 +
//     onStatus('error', err) 통지, save() 는 false 반환 (호출자가 전환 중단 등 판단).
//  5) 툴바 v1: h1/h2/h3, strong/em/u, link, blockquote, ul/ol.
//  6) 표·이미지는 execCommand 밖 — DOM 직접 조작으로 방언 요소(table/thead/tbody/tr/
//     td/th, img[src,alt])를 *생성*만 한다(신규 요소 없음). 서버 dialect.py 가 최종
//     정화·정규화 방어선. 이미지 업로드는 onUploadMedia(file)→{url} 콜백에 위임
//     (packages/doc 은 fetch 를 모른다 — API 호출은 web 쪽 책임).
//  7) 이미지 src: 정본은 `/media/{key}`. 마운트/삽입 시 apiBase 로 표시 절대경로로 매핑,
//     저장 직렬화 시 정본으로 되돌린다(media.js). apiBase 미지정이면 passthrough.
import { normalizeFragment, sanitizeUrl } from './dialect.js';
import { mediaSrcToDisplay, mediaSrcToCanonical, mapImgSrcs } from './media.js';

const AUTOSAVE_DELAY_MS = 2000;

// 툴바 명령 정의. execCommand 는 deprecated 지만 v1 에서 허용한다.
// TODO(v1): execCommand 대신 Selection/Range 기반 자체 명령으로 후속 교체.
const TOOLBAR = [
  { label: 'H1', title: '제목 1', cmd: 'formatBlock', value: 'h1' },
  { label: 'H2', title: '제목 2', cmd: 'formatBlock', value: 'h2' },
  { label: 'H3', title: '제목 3', cmd: 'formatBlock', value: 'h3' },
  { label: 'P', title: '본문', cmd: 'formatBlock', value: 'p' },
  { label: 'B', title: '굵게', cmd: 'bold' },
  { label: 'I', title: '기울임', cmd: 'italic' },
  { label: 'U', title: '밑줄', cmd: 'underline' },
  { label: '🔗', title: '링크', cmd: 'createLink' },
  { label: '❝', title: '인용', cmd: 'formatBlock', value: 'blockquote' },
  { label: '• 목록', title: '글머리 목록', cmd: 'insertUnorderedList' },
  { label: '1. 목록', title: '번호 목록', cmd: 'insertOrderedList' },
];

function runCommand(item, doc) {
  if (item.cmd === 'createLink') {
    const url = doc.defaultView?.prompt?.('링크 URL', 'https://');
    if (!url) return;
    doc.execCommand('createLink', false, url);
    return;
  }
  if (item.cmd === 'formatBlock') {
    doc.execCommand('formatBlock', false, item.value);
    return;
  }
  doc.execCommand(item.cmd, false, null);
}

// execCommand 밖 DOM 조작 버튼(표·이미지·표조작). action 은 handlers 맵의 키.
// 표조작 버튼은 셀 밖에서는 no-op — 항상 보이되 현재 셀 기준으로만 동작한다.
const SPECIAL_TOOLBAR = [
  { label: '⊞ 표', title: '표 삽입', action: 'insertTable' },
  { label: '🖼 이미지', title: '이미지 삽입', action: 'pickImage' },
  { label: '행+', title: '아래 행 추가', action: 'addRow' },
  { label: '행−', title: '현재 행 삭제', action: 'deleteRow' },
  { label: '열+', title: '왼쪽 열 추가', action: 'addColumn' },
  { label: '열−', title: '현재 열 삭제', action: 'deleteColumn' },
];

function buildToolbar(doc, article, onAfter, actions) {
  const bar = doc.createElement('div');
  bar.className = 'juldoc-toolbar';
  for (const item of TOOLBAR) {
    const btn = doc.createElement('button');
    btn.type = 'button';
    btn.textContent = item.label;
    btn.title = item.title;
    btn.dataset.cmd = item.cmd;
    btn.addEventListener('mousedown', (e) => e.preventDefault()); // 선택 유지
    btn.addEventListener('click', () => {
      article.focus();
      runCommand(item, doc);
      onAfter();
    });
    bar.appendChild(btn);
  }
  for (const item of SPECIAL_TOOLBAR) {
    const btn = doc.createElement('button');
    btn.type = 'button';
    btn.textContent = item.label;
    btn.title = item.title;
    btn.dataset.action = item.action;
    // 선택 유지: article.focus() 를 부르지 않고 현재 selection(셀/캐럿)을 보존한다.
    btn.addEventListener('mousedown', (e) => e.preventDefault());
    btn.addEventListener('click', () => actions[item.action]?.());
    bar.appendChild(btn);
  }
  return bar;
}

/**
 * 방언 정본 표 노드 생성 — 첫 행 thead(th), 나머지 tbody(td). 셀은 빈 채로 두고
 * article contenteditable 상속으로 편집한다.
 * @param {Document} doc
 * @param {number} rows 헤더 포함 전체 행 수
 * @param {number} cols 열 수
 * @returns {HTMLTableElement}
 */
export function createTable(doc, rows, cols) {
  const r = Math.max(1, rows | 0);
  const c = Math.max(1, cols | 0);
  const table = doc.createElement('table');

  const thead = doc.createElement('thead');
  const htr = doc.createElement('tr');
  for (let i = 0; i < c; i++) htr.appendChild(doc.createElement('th'));
  thead.appendChild(htr);
  table.appendChild(thead);

  const tbody = doc.createElement('tbody');
  for (let ri = 1; ri < r; ri++) {
    const tr = doc.createElement('tr');
    for (let i = 0; i < c; i++) tr.appendChild(doc.createElement('td'));
    tbody.appendChild(tr);
  }
  table.appendChild(tbody);
  return table;
}

/**
 * @param {Element} el 마운트 대상 컨테이너
 * @param {{
 *   html:string,
 *   onSave?:(html:string)=>any,
 *   onDirty?:(dirty:boolean)=>void,
 *   onStatus?:(state:'saving'|'saved'|'error', err?:Error)=>void,
 *   onUploadMedia?:(file:File)=>Promise<{url:string}>,
 *   apiBase?:string,
 * }} opts
 * @returns {{save:()=>Promise<boolean>, isDirty:()=>boolean, getHtml:()=>string,
 *   insertTable:(rows:number, cols:number)=>void, insertImage:(url:string, alt?:string)=>void,
 *   uploadAndInsertImage:(file:File)=>Promise<void>,
 *   addRow:()=>void, deleteRow:()=>void, addColumn:()=>void, deleteColumn:()=>void,
 *   destroy:()=>void}}
 */
export function mountEditor(el, { html, onSave, onDirty, onStatus, onUploadMedia, apiBase } = {}) {
  const doc = el.ownerDocument || document;

  el.innerHTML = html || '';
  const article = el.querySelector('article[data-juldoc]') || el.querySelector('article');
  if (!article) {
    throw new Error('mountEditor: 정본 <article data-juldoc="1"> 이 없습니다.');
  }
  // 정본 `/media/{key}` → 표시 절대경로. apiBase 미지정이면 passthrough(no-op).
  mapImgSrcs(article, (s) => mediaSrcToDisplay(s, apiBase));
  article.setAttribute('contenteditable', 'true');
  article.spellcheck = false;
  article.classList.add('juldoc-editor');

  // 이미지 선택용 숨은 file input (툴바 "이미지" 버튼이 click).
  const fileInput = doc.createElement('input');
  fileInput.type = 'file';
  fileInput.accept = 'image/*';
  fileInput.style.display = 'none';
  fileInput.addEventListener('change', () => {
    const file = fileInput.files?.[0];
    fileInput.value = ''; // 같은 파일 재선택 허용
    if (file) uploadAndInsertImage(file);
  });
  el.appendChild(fileInput);

  const actions = {
    insertTable: () => {
      const spec = doc.defaultView?.prompt?.('표 크기 (행x열)', '3x2');
      if (!spec) return;
      const m = /^(\d+)\s*[x×*]\s*(\d+)$/.exec(spec.trim());
      if (!m) return;
      insertTable(Number(m[1]), Number(m[2]));
    },
    pickImage: () => fileInput.click(),
    addRow,
    deleteRow,
    addColumn,
    deleteColumn,
  };

  const toolbar = buildToolbar(doc, article, () => markDirty(), actions);
  el.insertBefore(toolbar, article);

  let dirty = false;
  let saveTimer = null;

  function setDirty(next) {
    if (dirty === next) return;
    dirty = next;
    onDirty?.(dirty);
  }

  function markDirty() {
    setDirty(true);
    if (saveTimer) doc.defaultView?.clearTimeout(saveTimer);
    saveTimer = doc.defaultView?.setTimeout(() => save(), AUTOSAVE_DELAY_MS);
  }

  /**
   * 저장/외부용 직렬화 — 표시 img src 를 정본 `/media/{key}` 로 되돌린 outerHTML.
   * 라이브 DOM 은 건드리지 않도록 clone 에서 변환한다(표시 이미지가 저장 중 깨지지 않게).
   * apiBase 미지정이면 라이브 outerHTML 그대로(변환 불필요).
   */
  function serializeCanonical() {
    if (apiBase == null) return article.outerHTML;
    const clone = article.cloneNode(true);
    mapImgSrcs(clone, (s) => mediaSrcToCanonical(s, apiBase));
    return clone.outerHTML;
  }

  /**
   * 명시 저장 — article.outerHTML(래퍼 포함, 정본 img src) 을 onSave 로 전달.
   * 성공 시 dirty 해제 후 true, 실패 시 dirty *유지* + onStatus('error') 후 false.
   * (자동저장 타이머 경로에서도 같은 함수라 실패가 조용히 삼켜지지 않는다.)
   * @returns {Promise<boolean>} 저장 성공 여부
   */
  async function save() {
    if (saveTimer) {
      doc.defaultView?.clearTimeout(saveTimer);
      saveTimer = null;
    }
    const outer = serializeCanonical();
    if (onSave) {
      onStatus?.('saving');
      try {
        await onSave(outer);
      } catch (err) {
        // 실패: dirty 유지 (setDirty(false) 금지) — 재시도/재저장 가능해야 한다.
        onStatus?.('error', err);
        return false;
      }
    }
    // 저장 응답으로 DOM 을 교체하지 않는다(커서 점프 방지). dirty 만 해제.
    setDirty(false);
    onStatus?.('saved');
    return true;
  }

  function onInput() {
    markDirty();
  }

  /** paste/drop 공통 — 임의 HTML/텍스트를 방언 정규화해 삽입. */
  function insertSanitized(htmlData, textData) {
    const frag = htmlData
      ? normalizeFragment(htmlData, doc)
      : (() => {
          const f = doc.createDocumentFragment();
          f.appendChild(doc.createTextNode(textData || ''));
          return f;
        })();
    insertFragment(frag, doc);
    markDirty();
  }

  function onPaste(e) {
    // 이미지 파일(clipboard image) 우선 — 감지 시 업로드 경로로. (텍스트는 아래 정규화 경로.)
    const img = extractImageFile(e.clipboardData);
    if (img && onUploadMedia) {
      e.preventDefault();
      uploadAndInsertImage(img);
      return;
    }
    // paste 정규화: 허용 방언만 삽입 (UX용). 서버가 저장 시 최종 정화한다.
    e.preventDefault();
    const cb = e.clipboardData;
    insertSanitized(cb?.getData('text/html'), cb?.getData('text/plain'));
  }

  function onDrop(e) {
    // 드롭된 이미지 파일도 붙여넣기와 동일 업로드 경로.
    const img = extractImageFile(e.dataTransfer);
    if (img && onUploadMedia) {
      e.preventDefault();
      uploadAndInsertImage(img);
      return;
    }
    // drop 도 paste 와 동일 정규화 경로 — 브라우저 기본 삽입(비정화 HTML) 우회 차단.
    // TODO(v1): 드롭 지점 캐럿 이동(caretRangeFromPoint)은 후속 — 현재 선택 위치에 삽입.
    e.preventDefault();
    const dt = e.dataTransfer;
    insertSanitized(dt?.getData('text/html'), dt?.getData('text/plain'));
  }

  // ── 표·이미지 삽입/편집 (execCommand 밖, DOM 직접 조작) ──────────────

  /** 현재 선택 위치(article 내부)에 노드 삽입. 선택 없으면 article 끝에 append. */
  function insertNodeAtCursor(node) {
    const sel = doc.defaultView?.getSelection?.();
    if (sel && sel.rangeCount > 0 && article.contains(sel.getRangeAt(0).startContainer)) {
      const range = sel.getRangeAt(0);
      range.deleteContents();
      range.insertNode(node);
      range.setStartAfter(node);
      range.collapse(true);
      sel.removeAllRanges();
      sel.addRange(range);
    } else {
      article.appendChild(node);
    }
  }

  /** 커서 위치에 rows×cols 표 삽입(첫 행 thead). */
  function insertTable(rows, cols) {
    insertNodeAtCursor(createTable(doc, rows, cols));
    markDirty();
  }

  /** 커서 위치에 <img src alt> 삽입. src 는 sanitizeUrl 통과분만. */
  function insertImage(url, alt = '') {
    const safe = sanitizeUrl(url);
    if (!safe) return;
    const img = doc.createElement('img');
    img.setAttribute('src', safe);
    if (alt) img.setAttribute('alt', alt);
    insertNodeAtCursor(img);
    markDirty();
  }

  /**
   * 파일 업로드(onUploadMedia) → 응답 display_url 을 <img> 로 삽입. 실패해도 에디터 안 깨짐.
   *  - 업로드 전 클라 canvas 축소(최대 변 4096px)로 대역폭 절약 + 서버 MEDIA_003(4096 초과) 거부 방어.
   *  - 삽입 src 는 display_url(1600px webp) — 원본 url 아님(모바일 대역폭 절약이 여기서 동작).
   *    응답 url 은 정본 `/media/{key}` 이므로 apiBase 로 표시 절대경로로 매핑해 삽입(저장 시 정본 복원).
   *    (원본 url 은 data-original 로 남기지 않는다 — 방언 img 는 src/alt 만 허용해 서버 왕복에서 잘림.)
   */
  async function uploadAndInsertImage(file) {
    if (!onUploadMedia || !file) return;
    onStatus?.('saving'); // 업로드 중 표시(계약상 saving 재사용 — 삽입 후 자동저장이 saved 통지).
    try {
      // 축소는 UX/대역폭 장치일 뿐 — 서버가 최종 검증·variant 생성(서버 신뢰 안 함).
      // 축소 실패 시 downscaleImage 가 원본을 그대로 반환 → 서버가 거부하면 아래 catch 에서 표시.
      const toSend = await downscaleImage(file, doc);
      const res = await onUploadMedia(toSend);
      const url = res?.display_url || res?.url; // display_url 우선(본문용), 폴백은 원본.
      if (url) insertImage(mediaSrcToDisplay(url, apiBase), file.name || ''); // 정본→표시 매핑(passthrough if apiBase 미지정)
    } catch (err) {
      onStatus?.('error', err); // 실패(서버 MEDIA_003 거부 포함) 통지 — 삽입 없이 종료(에디터 유지).
    }
  }

  /** 현재 선택이 속한 td/th (없으면 null). */
  function currentCell() {
    const sel = doc.defaultView?.getSelection?.();
    if (!sel || sel.rangeCount === 0) return null;
    let node = sel.getRangeAt(0).startContainer;
    while (node && node !== article) {
      if (node.nodeType === 1 && /^(td|th)$/i.test(node.tagName)) return node;
      node = node.parentNode;
    }
    return null;
  }

  /** 현재 셀 아래(헤더면 tbody 맨 위)에 같은 열 수의 행 추가. */
  function addRow() {
    const cell = currentCell();
    if (!cell) return;
    const tr = cell.closest('tr');
    const table = cell.closest('table');
    let tbody = table.querySelector('tbody');
    if (!tbody) {
      tbody = doc.createElement('tbody');
      table.appendChild(tbody);
    }
    const newRow = doc.createElement('tr');
    for (let i = 0; i < tr.cells.length; i++) newRow.appendChild(doc.createElement('td'));
    if (tr.parentNode === tbody) tr.after(newRow);
    else tbody.insertBefore(newRow, tbody.firstChild);
    markDirty();
  }

  /** 현재 셀의 행 삭제(마지막 한 행은 남긴다). */
  function deleteRow() {
    const cell = currentCell();
    if (!cell) return;
    const table = cell.closest('table');
    if (table.rows.length <= 1) return;
    cell.closest('tr').remove();
    markDirty();
  }

  /** 현재 열 왼쪽에 열 추가(헤더 행은 th, 본문 행은 td). */
  function addColumn() {
    const cell = currentCell();
    if (!cell) return;
    const idx = cell.cellIndex;
    const table = cell.closest('table');
    for (const row of table.rows) {
      const header = row.parentNode.tagName.toLowerCase() === 'thead';
      const newCell = doc.createElement(header ? 'th' : 'td');
      row.insertBefore(newCell, row.cells[idx] || null);
    }
    markDirty();
  }

  /** 현재 열 삭제(마지막 한 열은 남긴다). */
  function deleteColumn() {
    const cell = currentCell();
    if (!cell) return;
    const table = cell.closest('table');
    if ((table.rows[0]?.cells.length || 0) <= 1) return;
    const idx = cell.cellIndex;
    for (const row of table.rows) {
      if (row.cells[idx]) row.deleteCell(idx);
    }
    markDirty();
  }

  article.addEventListener('input', onInput);
  article.addEventListener('paste', onPaste);
  article.addEventListener('drop', onDrop);

  return {
    save,
    isDirty: () => dirty,
    getHtml: () => serializeCanonical(),
    insertTable,
    insertImage,
    uploadAndInsertImage,
    addRow,
    deleteRow,
    addColumn,
    deleteColumn,
    destroy() {
      if (saveTimer) doc.defaultView?.clearTimeout(saveTimer);
      article.removeEventListener('input', onInput);
      article.removeEventListener('paste', onPaste);
      article.removeEventListener('drop', onDrop);
      el.innerHTML = '';
    },
  };
}

// ── 클라 이미지 축소 (업로드 전 대역폭 절약 + 서버 4096px 거부 방어) ──────────
// 서버 신뢰 안 함 원칙: 이 축소는 UX/대역폭 장치일 뿐이고, 서버가 최종 검증(4096 초과
// = MEDIA_003 거부)·variant(display/thumb) 생성의 정본이다. 축소 실패 시엔 원본을
// 그대로 올려 서버 판단에 맡긴다(그러면 큰 사진은 서버가 거부 → onStatus 로 표시).

export const MAX_UPLOAD_SIDE = 4096;

/**
 * 최대 변 maxSide 기준 축소 후 크기 계산(순수 함수). 이미 작으면 scaled=false.
 * @param {number} width
 * @param {number} height
 * @param {number} maxSide
 * @returns {{width:number, height:number, scaled:boolean}}
 */
export function computeScaledSize(width, height, maxSide) {
  const longest = Math.max(width, height);
  if (!(longest > maxSide)) return { width, height, scaled: false };
  const ratio = maxSide / longest;
  return {
    width: Math.max(1, Math.round(width * ratio)),
    height: Math.max(1, Math.round(height * ratio)),
    scaled: true,
  };
}

/** 파일명 확장자를 .webp 로 교체(없으면 append). 서버 로깅/표시용. */
function renameToWebp(name) {
  const base = (name || 'image').replace(/\.[^./\\]+$/, '');
  return `${base}.webp`;
}

/** 이미지 파일의 자연 크기 읽기 — 실패/미지원이면 null. */
function readImageSize(file, doc) {
  return new Promise((resolve) => {
    const view = doc.defaultView || globalThis;
    const makeUrl = view.URL?.createObjectURL;
    if (!makeUrl || typeof view.Image !== 'function') {
      resolve(null);
      return;
    }
    const url = makeUrl.call(view.URL, file);
    const img = new view.Image();
    const done = (val) => {
      view.URL.revokeObjectURL?.(url);
      resolve(val);
    };
    img.onload = () =>
      done({ width: img.naturalWidth || img.width, height: img.naturalHeight || img.height, image: img });
    img.onerror = () => done(null);
    img.src = url;
  });
}

/** 이미지를 w×h canvas 로 그려 webp Blob 반환 — 미지원/실패면 null. */
function drawToBlob(image, w, h, doc) {
  return new Promise((resolve) => {
    const canvas = doc.createElement('canvas');
    canvas.width = w;
    canvas.height = h;
    const ctx = canvas.getContext?.('2d');
    if (!ctx || typeof canvas.toBlob !== 'function') {
      resolve(null);
      return;
    }
    ctx.drawImage(image, 0, 0, w, h);
    canvas.toBlob((blob) => resolve(blob || null), 'image/webp', 0.85);
  });
}

/**
 * 업로드 전 클라 축소: 최대 변이 maxSide 초과면 canvas 로 리사이즈한 webp File 반환.
 * 이미 작거나 축소 불가(환경 미지원/실패)면 원본 file 을 그대로 반환.
 * @param {File} file
 * @param {Document} [doc]
 * @param {number} [maxSide]
 * @returns {Promise<File|Blob>}
 */
export async function downscaleImage(file, doc = document, maxSide = MAX_UPLOAD_SIDE) {
  try {
    const dims = await readImageSize(file, doc);
    if (!dims) return file;
    const target = computeScaledSize(dims.width, dims.height, maxSide);
    if (!target.scaled) return file; // 이미 작음 — 원본 그대로.
    const blob = await drawToBlob(dims.image, target.width, target.height, doc);
    if (!blob) return file; // canvas 미지원/실패 — 원본 그대로(서버가 판단).
    const view = doc.defaultView || globalThis;
    const FileCtor = view.File || globalThis.File;
    if (typeof FileCtor !== 'function') return blob;
    return new FileCtor([blob], renameToWebp(file.name), { type: 'image/webp' });
  } catch {
    return file; // 어떤 실패든 원본 그대로 — 서버가 최종 검증(거부 시 onStatus 표시).
  }
}

/**
 * DataTransfer/ClipboardData 에서 첫 이미지 파일을 뽑는다 (없으면 null).
 * files 우선, 없으면 items(kind==='file') 순회 — 브라우저별 편차 흡수.
 * @param {DataTransfer|null|undefined} dt
 * @returns {File|null}
 */
function extractImageFile(dt) {
  if (!dt) return null;
  const files = dt.files;
  if (files && files.length) {
    for (const f of files) {
      if (f && typeof f.type === 'string' && f.type.startsWith('image/')) return f;
    }
  }
  const items = dt.items;
  if (items && items.length) {
    for (const it of items) {
      if (it.kind === 'file' && typeof it.type === 'string' && it.type.startsWith('image/')) {
        const f = it.getAsFile?.();
        if (f) return f;
      }
    }
  }
  return null;
}

/** 현재 선택 위치에 정화된 fragment 를 삽입. */
function insertFragment(frag, doc) {
  const sel = doc.defaultView?.getSelection?.();
  if (!sel || sel.rangeCount === 0) return;
  const range = sel.getRangeAt(0);
  range.deleteContents();
  const last = frag.lastChild;
  range.insertNode(frag);
  if (last) {
    range.setStartAfter(last);
    range.collapse(true);
    sel.removeAllRanges();
    sel.addRange(range);
  }
}
