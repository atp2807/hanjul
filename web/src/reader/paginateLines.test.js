import { describe, expect, it } from 'vitest';

import { paginateLines } from './paginateLines';

// 가짜 measureLines — 줄 수/높이를 직접 지정 (Pretext/캔버스 불필요).
function fakeMeasure(spec) {
  // spec[block.id] = { lines: [...], lineHeight, marginBottom, fixedHeight }
  return (block) => spec[block.id];
}
const para = (id, n) => ({ id, type: 'P' });

describe('paginateLines', () => {
  it('블록 하나가 다 들어가면 1 페이지', () => {
    const blocks = [para('a')];
    const measureLines = fakeMeasure({ a: { lineHeight: 10, marginBottom: 0, lines: ['l1', 'l2', 'l3'] } });
    const pages = paginateLines(blocks, { contentHeight: 100, measureLines });
    expect(pages).toHaveLength(1);
    expect(pages[0][0].lines).toEqual(['l1', 'l2', 'l3']);
  });

  it('긴 블록이 페이지 경계에서 줄 단위로 쪼개진다', () => {
    const blocks = [para('a')];
    // 줄 10px × 5줄 = 50, 페이지 30 → 3줄 + 2줄
    const measureLines = fakeMeasure({ a: { lineHeight: 10, marginBottom: 0, lines: ['1', '2', '3', '4', '5'] } });
    const pages = paginateLines(blocks, { contentHeight: 30, measureLines });
    expect(pages).toHaveLength(2);
    expect(pages[0][0]).toMatchObject({ blockId: 'a', lines: ['1', '2', '3'] });
    expect(pages[1][0]).toMatchObject({ blockId: 'a', lines: ['4', '5'] });
  });

  it('쪼개진 조각은 같은 blockId 를 유지한다', () => {
    const blocks = [para('p1')];
    const measureLines = fakeMeasure({ p1: { lineHeight: 10, marginBottom: 0, lines: ['a', 'b', 'c', 'd'] } });
    const pages = paginateLines(blocks, { contentHeight: 20, measureLines });
    expect(pages.flat().every((f) => f.blockId === 'p1')).toBe(true);
  });

  it('줄이 하나도 유실되지 않는다', () => {
    const blocks = [para('a'), para('b')];
    const measureLines = fakeMeasure({
      a: { lineHeight: 10, marginBottom: 0, lines: ['a1', 'a2', 'a3'] },
      b: { lineHeight: 10, marginBottom: 0, lines: ['b1', 'b2'] },
    });
    const pages = paginateLines(blocks, { contentHeight: 25, measureLines });
    const allLines = pages.flat().flatMap((f) => f.lines);
    expect(allLines).toEqual(['a1', 'a2', 'a3', 'b1', 'b2']);
  });

  it('HR(fixedHeight)도 페이지에 배치된다', () => {
    const blocks = [{ id: 'hr', type: 'HR' }];
    const measureLines = fakeMeasure({ hr: { fixedHeight: 1, marginBottom: 10, lines: [] } });
    const pages = paginateLines(blocks, { contentHeight: 100, measureLines });
    expect(pages).toHaveLength(1);
    expect(pages[0][0].type).toBe('HR');
  });

  it('페이지가 작을수록 페이지 수가 늘어난다 (단조성)', () => {
    const blocks = [para('a')];
    const lines = Array.from({ length: 12 }, (_, i) => `L${i}`);
    const measureLines = fakeMeasure({ a: { lineHeight: 10, marginBottom: 0, lines } });
    const few = paginateLines(blocks, { contentHeight: 120, measureLines });
    const many = paginateLines(blocks, { contentHeight: 30, measureLines });
    expect(many.length).toBeGreaterThan(few.length);
  });
});
