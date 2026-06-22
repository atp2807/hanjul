// 중립 doc → 챕터 분리 (헤딩 기준). 원클릭 출판에서 백엔드 Book→Chapter→Block 으로 보냄.
// 헤딩 = 챕터 제목(본문 블록 아님), 그 아래 블록 = 챕터 본문. 첫 헤딩 전 본문 = 무제 챕터.
// 순수 — blocksToCanonical 로 정본 {type,html} 까지 변환해 반환.
import { blocksToCanonical } from './serialize';

const HEADINGS = new Set(['h1', 'h2', 'h3']);

export function splitIntoChapters(doc) {
  const chapters = [];
  let cur = null;
  const open = (title) => {
    cur = { title, neutral: [] };
    chapters.push(cur);
  };

  for (const b of doc.blocks || []) {
    if (HEADINGS.has(b.type)) {
      const title = (b.spans || []).map((s) => s.text).join('').trim() || null;
      open(title);
    } else {
      if (!cur) open(null); // 첫 헤딩 전 본문
      cur.neutral.push(b);
    }
  }

  return chapters.map((c) => ({ title: c.title, blocks: blocksToCanonical({ blocks: c.neutral }) }));
}
