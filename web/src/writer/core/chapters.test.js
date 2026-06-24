import { describe, expect, it } from 'vitest';

import { splitIntoChapters } from './chapters';

describe('splitIntoChapters', () => {
  it('헤딩마다 챕터, 제목=헤딩 텍스트, 본문=정본 블록', () => {
    const out = splitIntoChapters({
      blocks: [
        { type: 'h1', spans: [{ text: '1장', marks: [] }] },
        { type: 'p', spans: [{ text: '본문', marks: [] }] },
        { type: 'h1', spans: [{ text: '2장', marks: [] }] },
        { type: 'p', spans: [{ text: '다음', marks: [] }] },
      ],
    });
    expect(out).toEqual([
      { title: '1장', blocks: [{ type: 'P', html: '<p>본문</p>' }] },
      { title: '2장', blocks: [{ type: 'P', html: '<p>다음</p>' }] },
    ]);
  });

  it('첫 헤딩 전 본문은 무제 챕터(title=null)', () => {
    const out = splitIntoChapters({
      blocks: [
        { type: 'p', spans: [{ text: '서문', marks: [] }] },
        { type: 'h1', spans: [{ text: '1장', marks: [] }] },
      ],
    });
    expect(out[0]).toEqual({ title: null, blocks: [{ type: 'P', html: '<p>서문</p>' }] });
    expect(out[1]).toEqual({ title: '1장', blocks: [] });
  });

  it('장(h2)·절(h3)은 챕터 경계 아님 — 챕터 본문에 남는다', () => {
    const out = splitIntoChapters({
      blocks: [
        { type: 'h1', spans: [{ text: '1챕터', marks: [] }] },
        { type: 'h2', spans: [{ text: '1장', marks: [] }] },
        { type: 'p', spans: [{ text: '본문', marks: [] }] },
      ],
    });
    expect(out).toHaveLength(1); // 챕터 1개
    expect(out[0].title).toBe('1챕터');
    expect(out[0].blocks).toEqual([
      { type: 'H2', html: '<h2>1장</h2>' }, // 장은 본문 블록
      { type: 'P', html: '<p>본문</p>' },
    ]);
  });

  it('빈 문서 → 빈 챕터 목록', () => {
    expect(splitIntoChapters({ blocks: [] })).toEqual([]);
  });
});
