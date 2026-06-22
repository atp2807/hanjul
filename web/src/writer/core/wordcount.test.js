import { describe, expect, it } from 'vitest';

import { charCount, wordCount } from './wordcount';

const doc = {
  blocks: [
    { type: 'h1', spans: [{ text: '제목', marks: [] }] },
    { type: 'p', spans: [{ text: 'hello ', marks: [] }, { text: 'world', marks: ['strong'] }] },
    { type: 'hr' },
  ],
};

describe('wordcount', () => {
  it('charCount 는 hr 제외 글자수', () => {
    expect(charCount(doc)).toBe('제목'.length + 'hello world'.length);
  });

  it('wordCount 는 공백 단어 수', () => {
    expect(wordCount(doc)).toBe(3); // 제목 / hello / world
  });

  it('빈 문서는 0', () => {
    expect(charCount({ blocks: [] })).toBe(0);
    expect(wordCount({})).toBe(0);
  });
});
