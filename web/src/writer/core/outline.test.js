import { describe, expect, it } from 'vitest';

import { neutralToPmDoc } from '../editor/pm_doc';
import { docToOutline } from './outline';

const doc = neutralToPmDoc({
  blocks: [
    { type: 'h1', spans: [{ text: '1장 발단', marks: [] }] },
    { type: 'p', spans: [{ text: '주인공이 등장한다', marks: [] }] },
    { type: 'h2', spans: [{ text: '작은 절', marks: [] }] },
    { type: 'p', spans: [{ text: '짧다', marks: [] }] },
    { type: 'h1', spans: [{ text: '2장 전개', marks: [] }] },
    { type: 'p', spans: [{ text: '사건', marks: [] }] },
  ],
});

describe('docToOutline', () => {
  it('헤딩에서 목차를 만든다 (레벨·텍스트 순서)', () => {
    const o = docToOutline(doc);
    expect(o.map((h) => [h.level, h.text])).toEqual([
      [1, '1장 발단'],
      [2, '작은 절'],
      [1, '2장 전개'],
    ]);
  });

  it('섹션 글자수 = 다음 동급+ 헤딩 전까지', () => {
    const o = docToOutline(doc);
    expect(o[0].charCount).toBe('주인공이 등장한다'.length); // 다음 헤딩(h2)에서 평면 중단
    expect(o[1].charCount).toBe('짧다'.length);
    expect(o[2].charCount).toBe('사건'.length);
  });

  it('헤딩 없으면 빈 목차', () => {
    const empty = neutralToPmDoc({ blocks: [{ type: 'p', spans: [{ text: '본문만', marks: [] }] }] });
    expect(docToOutline(empty)).toEqual([]);
  });
});
