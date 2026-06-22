// DOCX 가져오기 어댑터 — mammoth(docx→html) + html→중립 doc.
// 어댑터 레이어라 DOM(DOMParser) 사용 OK (core 는 순수 유지). 결과 중립 doc 은
// neutralToPmDoc 로 에디터에 적재되고, 출판 시 정본까지 같은 경로.
import mammoth from 'mammoth';

import { MARKS } from '../core/blocks';

// HTML 블록 태그 → 중립 type (h4~6 은 h3 로 클램프, 우리 모델 h1~3)
const HEADING = { H1: 'h1', H2: 'h2', H3: 'h3', H4: 'h3', H5: 'h3', H6: 'h3' };

const withMark = (active, m) => MARKS.filter((x) => active.includes(x) || x === m);

function inlineSpans(node, active = []) {
  const spans = [];
  node.childNodes.forEach((child) => {
    if (child.nodeType === 3) {
      if (child.textContent) spans.push({ text: child.textContent, marks: [...active] });
    } else if (child.nodeType === 1) {
      const tag = child.tagName;
      const next =
        tag === 'STRONG' || tag === 'B' ? withMark(active, 'strong')
          : tag === 'EM' || tag === 'I' ? withMark(active, 'em')
            : active;
      spans.push(...inlineSpans(child, next));
    }
  });
  return spans;
}

const clean = (spans) => spans.filter((s) => s.text !== '');

// 통제되지 않은 HTML(mammoth 출력 등) → 중립 doc. 모르는 블록은 텍스트만 문단으로(손실 최소).
export function htmlToNeutral(html) {
  const doc = new DOMParser().parseFromString(html, 'text/html');
  const blocks = [];
  const push = (type, spans) => {
    if (type === 'hr') return blocks.push({ type });
    const c = clean(spans);
    if (c.length || type[0] === 'h') blocks.push({ type, spans: c }); // 빈 문단은 버림(빈 제목은 유지)
  };

  doc.body.childNodes.forEach((el) => {
    if (el.nodeType !== 1) return; // 블록 사이 공백 텍스트 무시
    const tag = el.tagName;
    if (HEADING[tag]) push(HEADING[tag], inlineSpans(el));
    else if (tag === 'P') push('p', inlineSpans(el));
    else if (tag === 'BLOCKQUOTE') push('quote', inlineSpans(el));
    else if (tag === 'HR') push('hr');
    else if (tag === 'UL' || tag === 'OL') {
      el.querySelectorAll('li').forEach((li) => push('p', inlineSpans(li)));
    } else if (tag === 'TABLE') {
      // 표 → 행마다 문단, 셀은 공백 구분(붙어버리지 않게)
      el.querySelectorAll('tr').forEach((tr) => {
        const cells = [...tr.querySelectorAll('th,td')].map((c) => c.textContent.trim()).filter(Boolean);
        if (cells.length) push('p', [{ text: cells.join('  '), marks: [] }]);
      });
    } else {
      push('p', inlineSpans(el)); // div 등 → 텍스트 문단
    }
  });
  return { blocks };
}

// 브라우저: File.arrayBuffer() → 중립 doc
export async function docxToNeutral(arrayBuffer) {
  const { value: html } = await mammoth.convertToHtml({ arrayBuffer });
  return htmlToNeutral(html);
}
