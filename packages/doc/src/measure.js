// measurer 어댑터 — 블록을 '시각적 줄' 단위로 분해해 페이지 분할에 넘긴다.
// Pretext(@chenglou/pretext)는 오직 이 파일에서만 import 한다 (격리 지점).
// hanjul/web/src/reader/pretextLineMeasurer.js 패턴 계승, juldoc 방언으로 확장.
//
// v2: 표는 셀 내용 기반 실측(행 단위 분할 지원), 인라인 굵기(strong/em)는
//     rich-inline 세그먼트 측정으로 혼합 굵기 줄바꿈을 정확화한다.
import { prepareWithSegments, layoutWithLines } from '@chenglou/pretext';
import {
  prepareRichInline,
  walkRichInlineLineRanges,
  materializeRichInlineLineRange,
} from '@chenglou/pretext/rich-inline';

const FONT_FAMILY =
  "-apple-system, BlinkMacSystemFont, 'Apple SD Gothic Neo', 'Segoe UI', Roboto, sans-serif";

/** 페이지 크기 프리셋 (px). a4 = 96dpi 기준 210×297mm 비율. */
export const PAGE_SIZES = {
  a4: { width: 794, height: 1123, padding: 64 },
  letter: { width: 816, height: 1056, padding: 64 },
};

// 표 셀 타이포/여백 (측정과 렌더가 공유해야 페이지 끝 잘림이 없다).
//   cellPadV/cellPadH: td/th 패딩(px, scale 전). cellBorder: 행 경계선(px).
const TABLE_CELL = { padV: 6, padH: 8, border: 1 };

// 블록 종류(대문자 태그명)별 타이포. 측정과 렌더가 같은 값을 써야 페이지 끝이
// 안 잘린다 (hanjul readerStyle 교훈: 측정 높이 ≠ 실제 높이면 잘림).
//   line 계열: fontPx/lineHeight 로 Pretext 측정.
//   fixed 계열(img): fixedHeight 로 텍스트 측정 생략.
//   pre: 개행 기준 코드 줄. list: 항목 수 기반 자체 측정.
//   table: rowHeight 는 node 없을 때(단위 테스트) 폴백용 근사.
const BLOCK_STYLE = {
  H1: { fontPx: 32, lineHeight: 44, marginBottom: 22, weight: 700 },
  H2: { fontPx: 26, lineHeight: 36, marginBottom: 18, weight: 700 },
  H3: { fontPx: 21, lineHeight: 30, marginBottom: 16, weight: 600 },
  H4: { fontPx: 18, lineHeight: 26, marginBottom: 14, weight: 600 },
  H5: { fontPx: 16, lineHeight: 24, marginBottom: 12, weight: 600 },
  H6: { fontPx: 15, lineHeight: 22, marginBottom: 12, weight: 600 },
  P: { fontPx: 18, lineHeight: 30, marginBottom: 16, weight: 400 },
  BLOCKQUOTE: { fontPx: 18, lineHeight: 30, marginBottom: 18, weight: 400 },
  PRE: { fontPx: 14, lineHeight: 22, marginBottom: 16, weight: 400, mono: true },
  UL: { fontPx: 18, lineHeight: 30, marginBottom: 16, weight: 400, perItem: true },
  OL: { fontPx: 18, lineHeight: 30, marginBottom: 16, weight: 400, perItem: true },
  TABLE: { fontPx: 15, lineHeight: 24, marginBottom: 18, weight: 400, rowHeight: 34 },
  IMG: { fontPx: 0, lineHeight: 0, marginBottom: 16, weight: 400, fixedHeight: 240 },
};

/** 블록 타입의 기본 스타일(미지정 타입은 P 로 폴백). */
export function blockStyle(type) {
  return BLOCK_STYLE[type] || BLOCK_STYLE.P;
}

/**
 * 렌더러가 측정과 동일한 타이포를 쓰도록, scale 적용된 스타일 값을 돌려준다.
 * @param {string} type 대문자 태그명
 * @param {number} scale
 */
export function scaledStyle(type, scale = 1) {
  const st = blockStyle(type);
  return {
    fontPx: (st.fontPx || 0) * scale,
    lineHeight: (st.lineHeight || 0) * scale,
    marginBottom: (st.marginBottom || 0) * scale,
    weight: st.weight || 400,
    mono: !!st.mono,
    fontFamily: FONT_FAMILY,
  };
}

/** 표 셀 렌더 상수를 scale 적용해 돌려준다 (reader 가 측정과 맞추는 용도). */
export function scaledTableCell(scale = 1) {
  return {
    padV: TABLE_CELL.padV * scale,
    padH: TABLE_CELL.padH * scale,
    border: TABLE_CELL.border,
    fontFamily: FONT_FAMILY,
  };
}

// ── 인라인 세그먼트 파싱 ────────────────────────────────────────────────
// 블록 내부 HTML 을 굵기/기울임 런(run) 배열로 평탄화한다.
//   strong/b → bold, em/i → italic (중첩 누적), u/a → 서식 없음(투명 통과),
//   br → 개행 세그먼트. dialect 정본(strong/em/u/a/br)과 정합.

/** 인접한 같은 서식 세그먼트를 합쳐 항목 수를 줄인다. */
function mergeSegments(segs) {
  const out = [];
  for (const s of segs) {
    const last = out[out.length - 1];
    if (last && last.bold === s.bold && last.italic === s.italic) {
      last.text += s.text;
    } else {
      out.push({ ...s });
    }
  }
  return out.filter((s) => s.text.length > 0);
}

/**
 * 블록 내부 HTML 을 [{text, bold, italic}] 세그먼트로 파싱.
 * DOMParser 사용(jsdom/브라우저 공통). 순수 함수 — 측정(canvas) 불필요.
 * @param {string} html
 * @returns {{text:string, bold:boolean, italic:boolean}[]}
 */
export function parseInlineSegments(html) {
  const doc = new DOMParser().parseFromString(`<div>${html || ''}</div>`, 'text/html');
  const root = doc.body.firstChild || doc.body;
  const segs = [];
  const walk = (node, bold, italic) => {
    for (const child of node.childNodes) {
      if (child.nodeType === 3) {
        // 텍스트 노드
        if (child.textContent) segs.push({ text: child.textContent, bold, italic });
      } else if (child.nodeType === 1) {
        const tag = child.tagName.toLowerCase();
        if (tag === 'br') {
          segs.push({ text: '\n', bold, italic });
          continue;
        }
        const b = bold || tag === 'strong' || tag === 'b';
        const i = italic || tag === 'em' || tag === 'i';
        walk(child, b, i); // u/a 등은 서식 변화 없이 자식만 순회
      }
    }
  };
  walk(root, false, false);
  const merged = mergeSegments(segs);
  return merged.length ? merged : [{ text: '', bold: false, italic: false }];
}

/** 세그먼트 서식에 맞는 canvas font 문자열. */
function segmentFont(st, fontPx, seg) {
  const weight = seg.bold ? 700 : st.weight || 400;
  const style = seg.italic ? 'italic ' : '';
  return `${style}${weight} ${fontPx}px ${FONT_FAMILY}`;
}

/**
 * 세그먼트를 강제 개행('\n', <br>/DOCX 줄바꿈) 경계로 그룹 분할.
 * 각 그룹은 하나의 '문단 조각'으로 독립 배치되고, 그룹 사이엔 하드 브레이크가 온다.
 * (pretext 는 whiteSpace 옵션 없이 '\n' 을 공백으로 접으므로 세그먼트 레벨에서 나눈다.)
 * @param {{text:string, bold:boolean, italic:boolean}[]} segs
 * @returns {{text:string, bold:boolean, italic:boolean}[][]}
 */
function splitSegmentsOnHardBreaks(segs) {
  const groups = [[]];
  for (const s of segs) {
    const parts = s.text.split('\n');
    parts.forEach((part, i) => {
      if (i > 0) groups.push([]); // '\n' 경계 → 새 그룹(하드 브레이크)
      if (part.length) groups[groups.length - 1].push({ text: part, bold: s.bold, italic: s.italic });
    });
  }
  return groups;
}

/**
 * 세그먼트 배열을 폭 제약으로 시각적 줄들로 배치한다. 강제 개행과 인라인 굵기를
 * 모두 반영한다. P/H/QUOTE 블록과 표 셀이 이 한 경로를 공유(측정=렌더 정합).
 *   - 서식 없는 그룹: keep-all 어절 줄바꿈(한국어 정확).
 *   - 서식 있는 그룹: rich-inline 세그먼트별 font 측정.
 *   - 그룹 경계('\n'): 무조건 새 줄.
 * @returns {{lines:string[], richLines:{runs:{text:string,bold:boolean,italic:boolean}[]}[]}}
 */
function layoutSegments(segs, { st, fontPx, contentWidth, lineHeight }) {
  const lines = [];
  const richLines = [];
  const plainFont = `${st.weight || 400} ${fontPx}px ${FONT_FAMILY}`;

  const pushEmpty = () => {
    lines.push('');
    richLines.push({ runs: [{ text: '', bold: false, italic: false }] });
  };

  for (const group of splitSegmentsOnHardBreaks(segs)) {
    if (group.length === 0) {
      pushEmpty(); // 빈 줄(연속 <br> 등) 보존
      continue;
    }
    const formatted = group.some((s) => s.bold || s.italic);

    if (!formatted) {
      const text = group.map((s) => s.text).join('');
      const prepared = prepareWithSegments(text, plainFont, { wordBreak: 'keep-all' });
      const { lines: gl } = layoutWithLines(prepared, contentWidth, lineHeight);
      if (gl.length === 0) {
        pushEmpty();
      } else {
        for (const ln of gl) {
          lines.push(ln.text);
          richLines.push({ runs: [{ text: ln.text, bold: false, italic: false }] });
        }
      }
      continue;
    }

    const items = group.map((s) => ({ text: s.text, font: segmentFont(st, fontPx, s) }));
    const prepared = prepareRichInline(items);
    let produced = 0;
    walkRichInlineLineRanges(prepared, contentWidth, (range) => {
      const line = materializeRichInlineLineRange(prepared, range);
      const runs = [];
      line.fragments.forEach((f, i) => {
        const seg = group[f.itemIndex] || { bold: false, italic: false };
        // gapBefore>0 = 항목 경계에서 접힌 공백 → 조인 시 되살린다.
        const text = i > 0 && f.gapBefore > 0 ? ` ${f.text}` : f.text;
        runs.push({ text, bold: !!seg.bold, italic: !!seg.italic });
      });
      richLines.push({ runs });
      lines.push(runs.map((r) => r.text).join(''));
      produced++;
    });
    if (produced === 0) pushEmpty(); // 공백만인 서식 그룹도 줄 하나로 보존
  }

  return { lines, richLines };
}

// ── 표 모델 파싱 ────────────────────────────────────────────────────────

/**
 * <table> 노드를 헤더/본문 행 모델로 파싱. 순수 함수(측정 불필요).
 * colspan/rowspan(병합)이 하나라도 있으면 splittable=false — 행 단위 분할 금지.
 * @param {Element} node
 * @returns {{splittable:boolean, columnCount:number,
 *   headerRows:{cells:object[]}[], bodyRows:{cells:object[]}[]}}
 */
export function parseTableModel(node) {
  // 이 표의 '직계' 행만 모은다 — table 직계 <tr> + 직계 thead/tbody/tfoot 의 직계 <tr>.
  // querySelectorAll('tr') 은 셀 안 중첩 표의 행까지 잡아 바깥 표를 오염시키므로 금지(#3).
  const directTrs = (el) => Array.from(el.children).filter((c) => c.tagName === 'TR');
  const rows = []; // {tr, inThead:boolean}
  for (const child of Array.from(node.children)) {
    const tag = child.tagName;
    if (tag === 'TR') rows.push({ tr: child, inThead: false });
    else if (tag === 'THEAD') for (const tr of directTrs(child)) rows.push({ tr, inThead: true });
    else if (tag === 'TBODY' || tag === 'TFOOT')
      for (const tr of directTrs(child)) rows.push({ tr, inThead: false });
  }

  let splittable = true;
  let columnCount = 0;
  const headerRows = [];
  const bodyRows = [];

  for (const { tr, inThead } of rows) {
    const cellEls = Array.from(tr.children).filter((c) => /^(TD|TH)$/.test(c.tagName));
    if (cellEls.length === 0) continue;
    let colsInRow = 0;
    const cells = cellEls.map((c) => {
      const colspan = parseInt(c.getAttribute('colspan') || '1', 10) || 1;
      const rowspan = parseInt(c.getAttribute('rowspan') || '1', 10) || 1;
      if (colspan > 1 || rowspan > 1) splittable = false;
      colsInRow += colspan;
      return {
        html: c.innerHTML,
        text: c.textContent || '',
        colspan,
        rowspan,
        header: c.tagName === 'TH',
      };
    });
    columnCount = Math.max(columnCount, colsInRow);

    const allTh = cellEls.every((c) => c.tagName === 'TH');
    // 헤더행: thead 안이거나, thead 없이 첫 행이 전부 <th> 인 경우.
    const isHeader = inThead || (headerRows.length === 0 && bodyRows.length === 0 && allTh);
    if (isHeader) headerRows.push({ cells });
    else bodyRows.push({ cells });
  }

  return { splittable, columnCount: Math.max(1, columnCount), headerRows, bodyRows };
}

/**
 * 표를 셀 내용 기반으로 실측한다. 각 행 높이 = max(셀 줄 수)*lineHeight + 패딩.
 * 셀 폭은 표 폭 / 열 수 균등분할 근사(정확한 자동 열폭 계산은 복잡 — 주석).
 * @returns {{table:true, splittable:boolean, marginBottom:number,
 *   headerRows:{height:number, cells:object[]}[], rows:{height:number, cells:object[]}[]}}
 */
function measureTable(node, contentWidth, st, scale) {
  const model = parseTableModel(node);
  const lineHeight = (st.lineHeight || 0) * scale;
  const fontPx = (st.fontPx || 0) * scale;
  const cell = scaledTableCell(scale);
  const cols = model.columnCount;
  // 근사: 열은 균등 폭. 각 열 = (표 폭/열수) - 좌우 패딩. colspan 은 그만큼 곱.
  const baseColWidth = contentWidth / cols;

  const measureRow = (row) => {
    let maxLines = 1;
    const cells = row.cells.map((c) => {
      const cellWidth = Math.max(1, baseColWidth * (c.colspan || 1) - 2 * cell.padH);
      // 셀도 인라인 세그먼트 기반 측정(strong/em·<br>) — P/H 와 동일 경로로 통일(#4).
      // 렌더는 td.innerHTML(c.html) 이므로 굵기·강제개행이 측정=렌더로 정합.
      // 헤더 셀(th)은 렌더가 600 굵기이므로 측정도 굵게(과소측정→잘림 방지).
      const cellStyle = c.header ? { ...st, weight: 700 } : st;
      const segs = parseInlineSegments(c.html || '');
      const { lines } = layoutSegments(segs, {
        st: cellStyle,
        fontPx,
        contentWidth: cellWidth,
        lineHeight,
      });
      const n = Math.max(1, lines.length);
      if (n > maxLines) maxLines = n;
      return { ...c, lines };
    });
    const height = maxLines * lineHeight + 2 * cell.padV + cell.border;
    return { height, cells };
  };

  return {
    table: true,
    splittable: model.splittable,
    marginBottom: (st.marginBottom || 0) * scale,
    headerRows: model.headerRows.map(measureRow),
    rows: model.bodyRows.map(measureRow),
  };
}

/**
 * measurer 팩토리. contentWidth 는 이미 scale 이 반영된 값(리더가 곱해 전달).
 * @param {{contentWidth:number, scale?:number}} opts
 * @returns {(block:object) => object}
 */
export function createMeasurer({ contentWidth, scale = 1 }) {
  return function measureLines(block) {
    const st = blockStyle(block.type);
    const marginBottom = (st.marginBottom || 0) * scale;
    const lineHeight = (st.lineHeight || 0) * scale;

    // 고정 높이(이미지) — 텍스트 측정 없이 한 단위.
    if (st.fixedHeight != null) {
      return { fixedHeight: st.fixedHeight * scale, marginBottom, lines: [] };
    }

    // 표: node 가 있으면 셀 실측(행 단위 분할 가능). 없거나 canvas 없으면(단위
    // 테스트/jsdom) rowCount 근사로 폴백 — 통짜 고정 높이.
    if (block.type === 'TABLE') {
      if (block.node) {
        try {
          return measureTable(block.node, contentWidth, st, scale);
        } catch {
          // canvas 부재(jsdom) 등 — 근사 폴백.
        }
      }
      const rows = Math.max(1, block.rowCount || 1);
      return { fixedHeight: rows * st.rowHeight * scale, marginBottom, lines: [] };
    }

    // 목록: 항목 수 * 줄높이 (v1 근사 — 항목 내 줄바꿈 무시, TODO).
    if (st.perItem) {
      const items = Math.max(1, block.itemCount || 1);
      return { fixedHeight: items * lineHeight, marginBottom, lines: [] };
    }

    // 코드: 개행 기준 줄 (가로 줄바꿈 없음 — 리더에서 overflow-x, TODO).
    if (block.type === 'PRE') {
      const codeLines = (block.text || '').split('\n');
      return { lineHeight, marginBottom, lines: codeLines };
    }

    // 문단/제목/인용: 인라인 세그먼트로 파싱해 굵기/기울임·강제개행을 반영해 측정.
    const fontPx = (st.fontPx || 0) * scale;
    const segs =
      block.html != null
        ? parseInlineSegments(block.html)
        : [{ text: block.text || '', bold: false, italic: false }];
    const hasFormatting = segs.some((s) => s.bold || s.italic);
    const hasHardBreak = segs.some((s) => s.text.includes('\n'));

    if (!hasFormatting && !hasHardBreak) {
      // 단일 굵기 + 강제개행 없음 — 기존 keep-all 어절 줄바꿈 경로(한국어 정확).
      const font = `${st.weight} ${fontPx}px ${FONT_FAMILY}`;
      const text = segs.map((s) => s.text).join('');
      const prepared = prepareWithSegments(text, font, { wordBreak: 'keep-all' });
      const { lines } = layoutWithLines(prepared, contentWidth, lineHeight);
      return { lineHeight, marginBottom, lines: lines.map((ln) => ln.text) };
    }

    // 혼합 굵기 또는 강제개행(<br>/DOCX '\n') — 공유 세그먼트 배치 경로.
    // 서식 없는 조각은 keep-all, 서식 있는 조각은 rich-inline, '\n' 은 하드 브레이크.
    // 렌더(reader)는 richLines 를 pre-wrap 으로 그대로 그리므로 측정=렌더 정합.
    const { lines, richLines } = layoutSegments(segs, { st, fontPx, contentWidth, lineHeight });
    if (lines.length === 0) {
      return { lineHeight, marginBottom, lines: [''], richLines: [{ runs: [{ text: '', bold: false, italic: false }] }] };
    }
    return { lineHeight, marginBottom, lines, richLines };
  };
}
