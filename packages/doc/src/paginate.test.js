// paginateLines 순수 함수 테스트 — 가짜 measurer 주입.
import { describe, it, expect } from 'vitest';
import { paginateLines } from './paginate.js';

// 각 블록이 정해진 줄 수/줄높이를 갖는 가짜 measurer.
function fakeMeasurer(spec) {
  return (block) => {
    const s = spec[block.type] ?? spec.default;
    if (s.fixedHeight != null) {
      return { fixedHeight: s.fixedHeight, marginBottom: s.marginBottom ?? 0, lines: [] };
    }
    const lines = Array.from({ length: block.lineCount ?? 1 }, (_, i) => `${block.id}-L${i}`);
    return { lineHeight: s.lineHeight, marginBottom: s.marginBottom ?? 0, lines };
  };
}

describe('paginateLines', () => {
  it('한 페이지에 다 들어가면 페이지 1개', () => {
    const blocks = [
      { id: 'b0', type: 'P', lineCount: 2 },
      { id: 'b1', type: 'P', lineCount: 2 },
    ];
    const measureLines = fakeMeasurer({ P: { lineHeight: 10 } });
    const pages = paginateLines(blocks, { contentHeight: 100, measureLines });
    expect(pages).toHaveLength(1);
    expect(pages[0]).toHaveLength(2);
  });

  it('넘치면 새 페이지로 분할', () => {
    const blocks = [
      { id: 'b0', type: 'P', lineCount: 6 },
      { id: 'b1', type: 'P', lineCount: 6 },
    ];
    const measureLines = fakeMeasurer({ P: { lineHeight: 10 } });
    // 페이지 높이 70 → 각 블록 60 만 들어가고 다음 블록은 다음 페이지.
    const pages = paginateLines(blocks, { contentHeight: 70, measureLines });
    expect(pages.length).toBeGreaterThanOrEqual(2);
  });

  it('긴 블록은 페이지 경계에서 줄 단위로 쪼개진다(같은 blockId 연속 페이지)', () => {
    const blocks = [{ id: 'b0', type: 'P', lineCount: 10 }];
    const measureLines = fakeMeasurer({ P: { lineHeight: 10 } });
    const pages = paginateLines(blocks, { contentHeight: 50, measureLines }); // 5줄/페이지
    expect(pages.length).toBe(2);
    expect(pages[0][0].blockId).toBe('b0');
    expect(pages[1][0].blockId).toBe('b0');
    // 모든 줄이 보존된다.
    const total = pages.flat().reduce((n, f) => n + f.lines.length, 0);
    expect(total).toBe(10);
  });

  it('richLines 가 lines 와 병행 분할된다', () => {
    const blocks = [{ id: 'b0', type: 'P', lineCount: 4 }];
    const measureLines = () => ({
      lineHeight: 10,
      marginBottom: 0,
      lines: ['L0', 'L1', 'L2', 'L3'],
      richLines: [
        { runs: [{ text: 'L0', bold: true, italic: false }] },
        { runs: [{ text: 'L1', bold: false, italic: false }] },
        { runs: [{ text: 'L2', bold: true, italic: false }] },
        { runs: [{ text: 'L3', bold: false, italic: false }] },
      ],
    });
    const pages = paginateLines(blocks, { contentHeight: 20, measureLines }); // 2줄/페이지
    expect(pages).toHaveLength(2);
    // 각 페이지 fragment 의 richLines 가 lines 와 1:1 로 따라간다.
    expect(pages[0][0].lines).toEqual(['L0', 'L1']);
    expect(pages[0][0].richLines.map((r) => r.runs[0].text)).toEqual(['L0', 'L1']);
    expect(pages[1][0].richLines.map((r) => r.runs[0].bold)).toEqual([true, false]);
  });

  describe('표 행 단위 분할', () => {
    const row = (h) => ({ height: h, cells: [{ text: 'x', html: 'x', colspan: 1, rowspan: 1, header: false }] });
    const tableMeasurer = (spec) => (block) => ({
      table: true,
      splittable: spec.splittable,
      marginBottom: 0,
      headerRows: spec.header ? [{ height: spec.headerH, cells: [{ text: 'H', html: 'H', colspan: 1, rowspan: 1, header: true }] }] : [],
      rows: spec.rows.map(row),
    });

    it('단순 표는 남는 공간까지 채우고 나머지는 다음 페이지 + 헤더 반복', () => {
      const blocks = [{ id: 't0', type: 'TABLE' }];
      // 헤더 20, 각 행 30, contentHeight 100 → 페이지당 (100-20)/30 = 2행.
      const measureLines = tableMeasurer({ splittable: true, header: true, headerH: 20, rows: [30, 30, 30, 30, 30] });
      const pages = paginateLines(blocks, { contentHeight: 100, measureLines });
      expect(pages.length).toBe(3); // 2 + 2 + 1
      // 모든 페이지의 표 fragment 에 헤더행이 반복된다.
      for (const p of pages) {
        const frag = p.find((f) => f.type === 'TABLE');
        expect(frag.table.headerRows).toHaveLength(1);
      }
      // 본문 행 총합 보존.
      const totalRows = pages.reduce((n, p) => n + p.find((f) => f.type === 'TABLE').table.rows.length, 0);
      expect(totalRows).toBe(5);
    });

    it('본문행 0개(헤더만) 단순 표도 사라지지 않고 헤더 fragment 로 렌더된다(#1)', () => {
      const blocks = [{ id: 't0', type: 'TABLE' }];
      const measureLines = tableMeasurer({ splittable: true, header: true, headerH: 20, rows: [] });
      const pages = paginateLines(blocks, { contentHeight: 100, measureLines });
      expect(pages.length).toBeGreaterThan(0); // 통째로 사라지면 0
      const frag = pages.flat().find((f) => f.type === 'TABLE');
      expect(frag).toBeTruthy();
      expect(frag.table.headerRows).toHaveLength(1);
      expect(frag.table.rows).toHaveLength(0);
    });

    it('병합 표(splittable=false)는 통짜 — 한 fragment 로 유지', () => {
      const blocks = [{ id: 't0', type: 'TABLE' }];
      const measureLines = tableMeasurer({ splittable: false, header: true, headerH: 20, rows: [30, 30, 30, 30, 30] });
      const warn = console.warn;
      const calls = [];
      console.warn = (m) => calls.push(m);
      const pages = paginateLines(blocks, { contentHeight: 100, measureLines });
      console.warn = warn;
      // 통짜 표 = 단일 fragment, 모든 행 한 곳에.
      const frags = pages.flat().filter((f) => f.type === 'TABLE');
      expect(frags).toHaveLength(1);
      expect(frags[0].table.rows).toHaveLength(5);
      expect(frags[0].table.splittable).toBe(false);
      // 페이지(100)보다 큰(20+150) 표라 잘림 경고 로그.
      expect(calls.length).toBeGreaterThan(0);
    });
  });

  it('고정 높이 블록(img/table)은 한 단위로 취급', () => {
    const blocks = [
      { id: 'b0', type: 'P', lineCount: 3 },
      { id: 'b1', type: 'IMG' },
    ];
    const measureLines = fakeMeasurer({
      P: { lineHeight: 10 },
      IMG: { fixedHeight: 40 },
    });
    const pages = paginateLines(blocks, { contentHeight: 45, measureLines });
    // P(30) 뒤 IMG(40) 는 45 를 넘겨 다음 페이지.
    expect(pages.length).toBe(2);
    expect(pages[1][0].blockId).toBe('b1');
    expect(pages[1][0].lines).toHaveLength(0);
  });
});
