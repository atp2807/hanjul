// mountReader(el, {html, scale, paperSize, apiBase}) — 정본 HTML 을 페이지로 조판해 실제 DOM 으로 렌더.
// 캔버스 전면 렌더 금지: 진짜 <div> 페이지 안에 진짜 블록 요소를 그린다.
//
// 프레임워크 무소속 코어 — React 래퍼(DocReader.jsx)가 ref 에 마운트한다.
// 이미지 src: 정본 `/media/{key}` 를 apiBase 로 표시 절대경로로 매핑해 렌더(media.js).
import { createMeasurer, scaledStyle, scaledTableCell, blockStyle, PAGE_SIZES } from './measure.js';
import { paginateLines } from './paginate.js';
import { mediaSrcToDisplay, mapImgSrcs } from './media.js';

// 원본 요소를 통째로 복제 렌더하는 타입(줄 분할 안 함).
//   UL/OL/IMG: v1 그대로. TABLE: 실측 분할 시 frag.table 로 재구성하고,
//   node 없는 근사 폴백(단위테스트/canvas 부재) 시엔 원본 복제로 처리.
const RENDER_ORIGINAL = new Set(['TABLE', 'UL', 'OL', 'IMG']);

/**
 * 정본 HTML 을 블록 배열로 파싱. type = 대문자 태그명.
 * apiBase 가 주어지면 파싱 단계에서 img src 를 표시 절대경로로 매핑(render 가 이 노드를 복제 렌더).
 * @param {string} html
 * @param {string|null} [apiBase]
 * @returns {object[]}
 */
function parseBlocks(html, apiBase) {
  const parsed = new DOMParser().parseFromString(html || '', 'text/html');
  const article = parsed.querySelector('article[data-juldoc]') || parsed.body;
  // 정본 `/media/{key}` → 표시 절대경로. apiBase 미지정이면 passthrough(no-op).
  mapImgSrcs(article, (s) => mediaSrcToDisplay(s, apiBase));
  const blocks = [];
  let i = 0;
  for (const node of Array.from(article.children)) {
    const type = node.tagName.toUpperCase();
    blocks.push({
      id: `b${i++}`,
      type,
      text: node.textContent || '',
      html: node.innerHTML || '', // 인라인 굵기(strong/em) 측정용
      itemCount: node.querySelectorAll(':scope > li').length,
      rowCount: node.querySelectorAll('tr').length,
      node,
    });
  }
  return blocks;
}

/** 텍스트 블록 요소 하나를 측정과 동일한 타이포로 스타일링. */
function styleTextBlock(el, type, scale) {
  const st = scaledStyle(type, scale);
  el.style.margin = '0';
  el.style.fontFamily = st.fontFamily;
  el.style.fontSize = `${st.fontPx}px`;
  el.style.lineHeight = `${st.lineHeight}px`;
  el.style.fontWeight = String(st.weight);
  el.style.whiteSpace = 'pre-wrap'; // 줄들을 준 그대로 유지
  el.style.wordBreak = 'keep-all';
}

/** 인라인 런({text,bold,italic})을 strong/em 태그로 복원해 요소에 추가. */
function appendRun(el, run, doc) {
  let node = doc.createTextNode(run.text);
  if (run.italic) {
    const em = doc.createElement('em');
    em.appendChild(node);
    node = em;
  }
  if (run.bold) {
    const strong = doc.createElement('strong');
    strong.appendChild(node);
    node = strong;
  }
  el.appendChild(node);
}

/** 분할된 표 fragment 를 실제 <table> 로 렌더(헤더행 반복 포함). */
function renderTableFragment(frag, doc, scale) {
  const model = frag.table;
  const st = scaledStyle('TABLE', scale);
  const cell = scaledTableCell(scale);
  const table = doc.createElement('table');
  table.style.margin = '0';
  table.style.width = '100%';
  table.style.tableLayout = 'fixed'; // 균등 열폭 — 측정(균등분할 근사)과 정합
  table.style.borderCollapse = 'collapse';

  const mkRow = (row) => {
    const tr = doc.createElement('tr');
    for (const c of row.cells) {
      const td = doc.createElement(c.header ? 'th' : 'td');
      if (c.colspan > 1) td.colSpan = c.colspan;
      if (c.rowspan > 1) td.rowSpan = c.rowspan;
      td.innerHTML = c.html; // 셀 인라인 서식/속성 보존
      td.style.border = `${cell.border}px solid #d9dce1`;
      td.style.padding = `${cell.padV}px ${cell.padH}px`;
      td.style.fontFamily = st.fontFamily;
      td.style.fontSize = `${st.fontPx}px`;
      td.style.lineHeight = `${st.lineHeight}px`;
      td.style.fontWeight = c.header ? '600' : String(st.weight);
      td.style.verticalAlign = 'top';
      td.style.textAlign = 'left';
      td.style.wordBreak = 'keep-all';
      tr.appendChild(td);
    }
    return tr;
  };

  if (model.headerRows && model.headerRows.length) {
    const thead = doc.createElement('thead');
    for (const r of model.headerRows) thead.appendChild(mkRow(r));
    table.appendChild(thead);
  }
  const tbody = doc.createElement('tbody');
  for (const r of model.rows) tbody.appendChild(mkRow(r));
  table.appendChild(tbody);
  return table;
}

/** 한 프래그먼트를 페이지 본문 요소로 렌더. */
function renderFragment(frag, blockById, doc, scale) {
  const block = blockById.get(frag.blockId);
  const type = frag.type;

  // 실측 분할된 표: 헤더 반복 포함 실제 <table> 로 재구성.
  if (type === 'TABLE' && frag.table) {
    return renderTableFragment(frag, doc, scale);
  }

  if (RENDER_ORIGINAL.has(type) && block) {
    // 목록/이미지(및 근사 폴백 표): 원본 노드를 이 document 로 가져와 통째 렌더.
    const clone = doc.importNode(block.node, true);
    clone.style.margin = '0';
    clone.style.maxWidth = '100%';
    if (type === 'IMG') {
      // 측정-렌더 합의: measure.js 가 IMG 를 fixedHeight 로 측정하므로 렌더도
      // 같은 높이 상한을 강제한다 (넘치면 페이지 끝이 잘리는 불일치 방지).
      const fixedHeight = blockStyle('IMG').fixedHeight * scale;
      clone.style.display = 'block';
      clone.style.maxHeight = `${fixedHeight}px`;
      clone.style.objectFit = 'contain';
    }
    return clone;
  }

  if (type === 'PRE') {
    const pre = doc.createElement('pre');
    const code = doc.createElement('code');
    code.textContent = frag.lines.join('\n');
    const st = scaledStyle('PRE', scale);
    pre.style.margin = '0';
    pre.style.fontFamily = 'ui-monospace, SFMono-Regular, Menlo, Consolas, monospace';
    pre.style.fontSize = `${st.fontPx}px`;
    pre.style.lineHeight = `${st.lineHeight}px`;
    pre.style.whiteSpace = 'pre';
    pre.style.overflowX = 'auto'; // TODO(v1): 코드 가로 줄바꿈은 스크롤로 처리
    pre.appendChild(code);
    return pre;
  }

  // 텍스트 블록(h1~h6/p/blockquote): 그 페이지에 배정된 시각적 줄들을 렌더.
  const tag = type.toLowerCase();
  const el = doc.createElement(tag);
  styleTextBlock(el, type, scale);
  if (frag.richLines) {
    // 인라인 굵기 보존 — 측정한 줄별 런을 strong/em 으로 복원(줄 사이 개행).
    frag.richLines.forEach((line, i) => {
      if (i > 0) el.appendChild(doc.createTextNode('\n'));
      for (const run of line.runs) appendRun(el, run, doc);
    });
  } else {
    el.textContent = frag.lines.join('\n');
  }
  return el;
}

/** 페이지 컨테이너 div 를 만든다 (측정과 일치하는 고정 geometry). */
function renderPage(frags, page, scale, blockById, doc) {
  const pageEl = doc.createElement('div');
  pageEl.className = 'juldoc-page';
  const pad = page.padding * scale;
  pageEl.style.boxSizing = 'border-box';
  pageEl.style.width = `${page.width * scale}px`;
  pageEl.style.height = `${page.height * scale}px`;
  pageEl.style.padding = `${pad}px`;
  pageEl.style.overflow = 'hidden';

  for (const frag of frags) {
    const body = renderFragment(frag, blockById, doc, scale);
    const st = scaledStyle(frag.type, scale);
    body.style.marginBottom = `${st.marginBottom}px`;
    pageEl.appendChild(body);
  }
  return pageEl;
}

/**
 * 정본 HTML 을 페이지 조판 뷰로 렌더한다.
 * @param {Element} el 마운트 대상 컨테이너
 * @param {{html:string, scale?:number, paperSize?:string, apiBase?:string}} opts
 * @returns {{pageCount:number, destroy:Function}}
 */
export function mountReader(el, { html, scale = 1, paperSize = 'a4', apiBase } = {}) {
  const page = PAGE_SIZES[paperSize] || PAGE_SIZES.a4;
  const doc = el.ownerDocument || document;

  const contentWidth = (page.width - page.padding * 2) * scale;
  const contentHeight = (page.height - page.padding * 2) * scale;

  const blocks = parseBlocks(html, apiBase);
  const blockById = new Map(blocks.map((b) => [b.id, b]));
  const measureLines = createMeasurer({ contentWidth, scale });
  const pages = paginateLines(blocks, { contentHeight, measureLines });

  el.innerHTML = '';
  el.classList.add('juldoc-reader');
  for (const frags of pages) {
    el.appendChild(renderPage(frags, page, scale, blockById, doc));
  }

  return {
    pageCount: pages.length,
    destroy() {
      el.innerHTML = '';
      el.classList.remove('juldoc-reader');
    },
  };
}
