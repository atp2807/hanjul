// 줄 단위 페이지네이션 (순수). 긴 블록을 페이지 경계에서 줄 단위로 쪼갠다.
// measureLines(block) -> { lineHeight, marginBottom, lines: string[], fixedHeight? }
//   lines = Pretext 가 계산한 시각적 줄들(어절 단위 줄바꿈 반영). HR 등은 fixedHeight.
//
// 출력: pages = [[fragment, ...], ...]
//   fragment = { blockId, type, lines: string[] }  (이 페이지에 들어간 그 블록의 줄들)
//   한 블록이 두 페이지에 걸치면 같은 blockId 의 fragment 가 연속 페이지에 나뉘어 나온다.
export function paginateLines(blocks, { contentHeight, measureLines }) {
  const pages = [];
  let current = [];
  let used = 0;

  const breakPage = () => {
    pages.push(current);
    current = [];
    used = 0;
  };

  for (const block of blocks) {
    const m = measureLines(block);
    const isFixed = m.fixedHeight != null;
    const unitH = isFixed ? m.fixedHeight : m.lineHeight;
    const units = isFixed ? [null] : m.lines; // HR = 단위 1개

    let frag = null;
    for (const lineText of units) {
      if (used + unitH > contentHeight && current.length > 0) {
        breakPage();
        frag = null;
      }
      if (!frag) {
        frag = { blockId: block.id, type: block.type, lines: [] };
        current.push(frag);
      }
      if (lineText != null) frag.lines.push(lineText);
      used += unitH;
    }
    used += m.marginBottom; // 블록 하단 여백 (페이지 분할 강제는 안 함)
  }

  if (current.length > 0) pages.push(current);
  return pages;
}
