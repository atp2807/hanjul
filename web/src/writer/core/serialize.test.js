import { describe, expect, it } from 'vitest';

import { blocksToCanonical, canonicalToBlocks } from './serialize';

const doc = {
  blocks: [
    { type: 'h1', spans: [{ text: '제목', marks: [] }] },
    { type: 'p', spans: [{ text: '평범한 ', marks: [] }, { text: '강조', marks: ['strong'] }, { text: ' 문단 < > &', marks: [] }] },
    { type: 'quote', spans: [{ text: '인용', marks: ['em'] }] },
    { type: 'hr' },
  ],
};

describe('blocksToCanonical', () => {
  it('정본 코드 + HTML 로 직렬화 (마크·이스케이프 포함)', () => {
    const out = blocksToCanonical(doc);
    expect(out[0]).toEqual({ type: 'H1', html: '<h1>제목</h1>' });
    expect(out[1]).toEqual({
      type: 'P',
      html: '<p>평범한 <strong>강조</strong> 문단 &lt; &gt; &amp;</p>',
    });
    expect(out[2]).toEqual({ type: 'QUOTE', html: '<blockquote><em>인용</em></blockquote>' });
    expect(out[3]).toEqual({ type: 'HR', html: '<hr/>' });
  });
});

describe('round-trip', () => {
  it('canonical → blocks → canonical 가 안정적이다', () => {
    const canonical = blocksToCanonical(doc);
    const back = blocksToCanonical(canonicalToBlocks(canonical));
    expect(back).toEqual(canonical);
  });

  it('백엔드 text_to_blocks 출력(마크 없음)도 읽는다', () => {
    const fromBackend = [
      { type: 'P', html: '<p>그냥 문단</p>' },
      { type: 'HR', html: '<hr/>' },
    ];
    const neutral = canonicalToBlocks(fromBackend);
    expect(neutral.blocks[0]).toEqual({ type: 'p', spans: [{ text: '그냥 문단', marks: [] }] });
    expect(neutral.blocks[1]).toEqual({ type: 'hr' });
  });
});
