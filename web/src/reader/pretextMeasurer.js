// Pretext 기반 블록 높이 측정기 — 브라우저 Canvas 네이티브 사용(폴리필 불필요).
// CJK 한글은 wordBreak:'keep-all' 로 어절 단위 줄바꿈 (백엔드 PoC에서 실측 검증, lr-9fd9d241).
import { prepare, layout } from '@chenglou/pretext';

import { blockStyle, READER_STYLE } from './readerStyle';

// 정본 HTML 조각에서 측정용 평문 추출 (인라인 태그 제거 + 엔티티 복원).
function plainText(html) {
  return html
    .replace(/<[^>]+>/g, '')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&amp;/g, '&')
    .trim();
}

// scale = 폰트 배율(독자가 글자 크기 변경). contentWidth = 페이지 본문 너비(px).
export function createPretextMeasurer({ contentWidth, scale = 1 }) {
  return function measure(block) {
    const st = blockStyle(block.type);
    const marginBottom = st.marginBottom * scale;

    if (st.fixedHeight) {
      return st.fixedHeight * scale + marginBottom;
    }

    const fontPx = st.fontPx * scale;
    const lineHeight = st.lineHeight * scale;
    const font = `${st.weight} ${fontPx}px ${READER_STYLE.fontFamily}`;
    const prepared = prepare(plainText(block.html), font, { wordBreak: 'keep-all' });
    const { height } = layout(prepared, contentWidth, lineHeight);
    return height + marginBottom;
  };
}
