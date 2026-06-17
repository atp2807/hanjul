// 페이지네이션 알고리즘 (순수). 블록 높이를 재는 `measure`를 주입받아
// Pretext(캔버스 의존)와 분리 → 캔버스 없이 단위 테스트 가능.
//
// measure(block) -> 블록의 총 높이(px, 하단 여백 포함).
// contentHeight 를 넘기면 새 페이지로. 한 블록이 페이지보다 크면 그 블록만 단독 배치.
export function paginate(blocks, { contentHeight, measure }) {
  const pages = [];
  let current = [];
  let used = 0;

  for (const block of blocks) {
    const h = measure(block);
    if (current.length > 0 && used + h > contentHeight) {
      pages.push(current);
      current = [];
      used = 0;
    }
    current.push(block);
    used += h;
  }
  if (current.length > 0) pages.push(current);
  return pages;
}
