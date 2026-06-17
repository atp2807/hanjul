// 리더 스타일 단일 소스 — 측정(Pretext)과 렌더(CSS)가 같은 값을 쓰도록.
// 어긋나면 측정 높이 ≠ 실제 높이 → 페이지 끝이 잘린다 (linklore PoC 교훈).
export const READER_STYLE = {
  fontFamily:
    "-apple-system, BlinkMacSystemFont, 'Apple SD Gothic Neo', 'Segoe UI', Roboto, sans-serif",
  page: { width: 600, height: 800, padding: 32 },
  // 블록 종류별 타이포 (px). fixedHeight 가 있으면 텍스트 측정 대신 그 값 사용.
  blocks: {
    P: { fontPx: 18, lineHeight: 30, marginBottom: 16, weight: 400 },
    H1: { fontPx: 30, lineHeight: 42, marginBottom: 22, weight: 700 },
    H2: { fontPx: 24, lineHeight: 34, marginBottom: 18, weight: 700 },
    H3: { fontPx: 20, lineHeight: 30, marginBottom: 16, weight: 600 },
    QUOTE: { fontPx: 18, lineHeight: 30, marginBottom: 16, weight: 400 },
    HR: { fontPx: 0, lineHeight: 0, marginBottom: 24, weight: 400, fixedHeight: 1 },
  },
};

export function blockStyle(type) {
  return READER_STYLE.blocks[type] || READER_STYLE.blocks.P;
}
