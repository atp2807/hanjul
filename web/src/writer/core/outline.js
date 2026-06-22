// PM doc → 자동 목차 (헤딩에서 파생). 작가는 만들 게 없다 — 제목만 쓰면 생김.
// 각 항목: 제목·레벨·문서 내 위치(점프용)·섹션 글자수(자동 신호). 순수(prosemirror-model만).

export function docToOutline(pmDoc) {
  // top-level 블록 수집 (위치·글자수)
  const blocks = [];
  pmDoc.forEach((node, offset) => {
    blocks.push({ node, pos: offset, chars: node.isTextblock ? node.textContent.length : 0 });
  });

  const headingIdx = blocks
    .map((b, i) => (b.node.type.name === 'heading' ? i : -1))
    .filter((i) => i >= 0);

  return headingIdx.map((idx, k) => {
    const h = blocks[idx];
    // 섹션 글자수 = 이 제목 바로 아래 본문 (다음 헤딩 전까지, 평면)
    let chars = 0;
    for (let j = idx + 1; j < blocks.length; j++) {
      if (blocks[j].node.type.name === 'heading') break;
      chars += blocks[j].chars;
    }
    return {
      id: `h${k}`,
      level: h.node.attrs.level,
      text: h.node.textContent || '(제목 없음)',
      pos: h.pos,
      charCount: chars,
    };
  });
}
