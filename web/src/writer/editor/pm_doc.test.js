import { describe, expect, it } from 'vitest';

import { blocksToCanonical } from '../core/serialize';
import { neutralToPmDoc, pmToNeutral } from './pm_doc';

const neutral = {
  blocks: [
    { type: 'h2', spans: [{ text: '장 제목', marks: [] }] },
    { type: 'p', spans: [{ text: '본문 ', marks: [] }, { text: '강조', marks: ['strong', 'em'] }] },
    { type: 'quote', spans: [{ text: '인용', marks: [] }] },
    { type: 'hr' },
  ],
};

describe('pm_doc 변환', () => {
  it('neutral → PM → neutral 라운드트립', () => {
    const back = pmToNeutral(neutralToPmDoc(neutral));
    expect(back).toEqual(neutral);
  });

  it('PM 문서가 정본 직렬화까지 이어진다 (전 체인)', () => {
    const canonical = blocksToCanonical(pmToNeutral(neutralToPmDoc(neutral)));
    expect(canonical[0]).toEqual({ type: 'H2', html: '<h2>장 제목</h2>' });
    expect(canonical[1].html).toBe('<p>본문 <strong><em>강조</em></strong></p>');
    expect(canonical[3]).toEqual({ type: 'HR', html: '<hr/>' });
  });

  it('빈 문단도 안전 (빈 텍스트 노드 미생성)', () => {
    const doc = neutralToPmDoc({ blocks: [{ type: 'p', spans: [] }] });
    expect(pmToNeutral(doc)).toEqual({ blocks: [{ type: 'p', spans: [] }] });
  });
});
