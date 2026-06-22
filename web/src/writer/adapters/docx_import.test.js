import { readFileSync } from 'node:fs';

import mammoth from 'mammoth';
import { describe, expect, it } from 'vitest';

import { blocksToCanonical } from '../core/serialize';
import { htmlToNeutral } from './docx_import';

describe('htmlToNeutral', () => {
  it('헤딩/문단/인라인 마크 매핑', () => {
    const n = htmlToNeutral('<h1>제목</h1><p>본문 <strong>굵게</strong> <em>기울임</em></p>');
    expect(n.blocks[0]).toEqual({ type: 'h1', spans: [{ text: '제목', marks: [] }] });
    expect(n.blocks[1].type).toBe('p');
    expect(n.blocks[1].spans).toEqual([
      { text: '본문 ', marks: [] },
      { text: '굵게', marks: ['strong'] },
      { text: ' ', marks: [] },
      { text: '기울임', marks: ['em'] },
    ]);
  });

  it('h4~6 → h3 클램프, blockquote → quote, 목록 → 문단', () => {
    const n = htmlToNeutral('<h5>소제목</h5><blockquote>인용</blockquote><ul><li>가</li><li>나</li></ul>');
    expect(n.blocks.map((b) => b.type)).toEqual(['h3', 'quote', 'p', 'p']);
    expect(n.blocks[3].spans[0].text).toBe('나');
  });

  it('빈 문단은 버림', () => {
    expect(htmlToNeutral('<p></p><p>실내용</p>').blocks).toHaveLength(1);
  });

  it('표 → 행마다 문단, 셀 공백 구분(붙지 않음)', () => {
    const n = htmlToNeutral('<table><tr><td>가</td><td>나</td></tr><tr><td>다</td><td>라</td></tr></table>');
    expect(n.blocks.map((b) => b.spans[0].text)).toEqual(['가  나', '다  라']);
  });
});

describe('mammoth 통합 (실제 .docx 픽스처)', () => {
  it('docx → html → 중립 → 정본까지 관통', async () => {
    const buffer = readFileSync('e2e/fixtures/sample.docx'); // vitest cwd = web/
    const { value: html } = await mammoth.convertToHtml({ buffer });
    const neutral = htmlToNeutral(html);

    expect(neutral.blocks[0]).toEqual({ type: 'h1', spans: [{ text: '1장 도입', marks: [] }] });
    // 정본 직렬화까지 (인라인 서식 보존)
    const canonical = blocksToCanonical(neutral);
    expect(canonical[0]).toEqual({ type: 'H1', html: '<h1>1장 도입</h1>' });
    expect(canonical[1].html).toContain('<strong>굵게</strong>');
    expect(canonical[1].html).toContain('<em>기울임</em>');
    expect(neutral.blocks.some((b) => b.type === 'h2' && b.spans[0].text === '2장 전개')).toBe(true);
  });
});
