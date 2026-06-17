// Pretext 로 블록을 '시각적 줄' 단위로 분해 — 줄 단위 페이지 분할용.
// layoutWithLines 가 어절 단위(keep-all) 줄바꿈을 반영한 line 범위를 준다.
import { layoutWithLines, prepareWithSegments } from '@chenglou/pretext';

import { blockStyle, READER_STYLE } from './readerStyle';

function plainText(html) {
  return html
    .replace(/<[^>]+>/g, '')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&amp;/g, '&')
    .trim();
}

export function createPretextLineMeasurer({ contentWidth, scale = 1 }) {
  return function measureLines(block) {
    const st = blockStyle(block.type);
    const marginBottom = st.marginBottom * scale;

    if (st.fixedHeight) {
      return { fixedHeight: st.fixedHeight * scale, marginBottom, lines: [] };
    }

    const fontPx = st.fontPx * scale;
    const lineHeight = st.lineHeight * scale;
    const font = `${st.weight} ${fontPx}px ${READER_STYLE.fontFamily}`;
    const text = plainText(block.html);
    const prepared = prepareWithSegments(text, font, { wordBreak: 'keep-all' });
    const { lines } = layoutWithLines(prepared, contentWidth, lineHeight);
    return {
      lineHeight,
      marginBottom,
      lines: lines.map((ln) => text.slice(ln.start, ln.end)),
    };
  };
}
