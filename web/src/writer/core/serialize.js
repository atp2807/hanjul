// 중립 doc ↔ 정본 {type, html} 직렬화 (⚙️ 에디터↔출판 이음매). 순수 함수.
//
// 중립 doc 형태:
//   { blocks: [ Block ] }
//   Block = { type: 'p'|'h1'|'h2'|'h3'|'quote', spans: [Span] }  |  { type: 'hr' }
//   Span  = { text: string, marks: ('strong'|'em')[] }
//
// 정본은 우리가 생성/소비하는 통제된 HTML 부분집합이라(백엔드 text_to_blocks 와 동일 문법)
// 임의 HTML 파서 없이 한정 문법 파서로 충분 — DOM 비의존(데스크톱 이식성).

import { CODE_TO_NEUTRAL, MARKS, NEUTRAL_TO_CODE, NEUTRAL_TO_TAG } from './blocks';

const ESCAPE = [[/&/g, '&amp;'], [/</g, '&lt;'], [/>/g, '&gt;']];
const UNESCAPE = [[/&lt;/g, '<'], [/&gt;/g, '>'], [/&amp;/g, '&']];
const escape = (s) => ESCAPE.reduce((a, [re, r]) => a.replace(re, r), s);
const unescape = (s) => UNESCAPE.reduce((a, [re, r]) => a.replace(re, r), s);

function spansToHtml(spans) {
  return (spans || [])
    .map((sp) => {
      let h = escape(sp.text);
      // 고정 순서로 감싸 결정성 유지
      for (const m of MARKS) if (sp.marks?.includes(m)) h = `<${m}>${h}</${m}>`;
      return h;
    })
    .join('');
}

// 중립 doc → 정본 블록 리스트 (출판/저장용)
export function blocksToCanonical(doc) {
  return (doc.blocks || []).map((b) => {
    if (b.type === 'hr') return { type: NEUTRAL_TO_CODE.hr, html: '<hr/>' };
    const tag = NEUTRAL_TO_TAG[b.type];
    return { type: NEUTRAL_TO_CODE[b.type], html: `<${tag}>${spansToHtml(b.spans)}</${tag}>` };
  });
}

// 한정 인라인 파서 — <strong>/<em>(중첩 허용) + 텍스트. 인접 동일마크 런은 병합.
function parseInline(html) {
  const out = [];
  const re = /<(\/?)(strong|em)>|([^<]+)/g;
  const active = new Set();
  let m;
  while ((m = re.exec(html))) {
    if (m[3] != null) {
      const text = unescape(m[3]);
      if (text.length) out.push({ text, marks: MARKS.filter((x) => active.has(x)) });
    } else if (m[1] === '/') {
      active.delete(m[2]);
    } else {
      active.add(m[2]);
    }
  }
  return out;
}

function stripOuter(html) {
  const m = html.match(/^<([a-z0-9]+)>([\s\S]*)<\/\1>$/i);
  return m ? m[2] : html;
}

// 정본 블록 리스트 → 중립 doc (기존 책을 에디터로 불러올 때)
export function canonicalToBlocks(list) {
  return {
    blocks: (list || []).map((b) => {
      const type = CODE_TO_NEUTRAL[b.type];
      if (type === 'hr') return { type: 'hr' };
      return { type, spans: parseInline(stripOuter(b.html)) };
    }),
  };
}
