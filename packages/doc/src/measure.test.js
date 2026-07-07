// measure 어댑터 테스트 — jsdom 에는 canvas 가 없으므로 텍스트 측정(Pretext) 경로는
// 건드리지 않고, 고정 높이/표/목록 경로와 스타일 스케일 등 어댑터 형태만 검증한다.
import { describe, it, expect } from 'vitest';
import {
  createMeasurer,
  scaledStyle,
  blockStyle,
  PAGE_SIZES,
  parseInlineSegments,
  parseTableModel,
} from './measure.js';

describe('createMeasurer (canvas 불필요 경로)', () => {
  const measure = createMeasurer({ contentWidth: 600, scale: 1 });

  it('이미지는 고정 높이 단위', () => {
    const m = measure({ type: 'IMG' });
    expect(m.fixedHeight).toBeGreaterThan(0);
    expect(m.lines).toEqual([]);
  });

  it('표는 행 수 * 행높이', () => {
    const one = measure({ type: 'TABLE', rowCount: 1 }).fixedHeight;
    const three = measure({ type: 'TABLE', rowCount: 3 }).fixedHeight;
    expect(three).toBeCloseTo(one * 3);
  });

  it('목록은 항목 수 * 줄높이', () => {
    const m = measure({ type: 'UL', itemCount: 4 });
    expect(m.fixedHeight).toBeGreaterThan(0);
    expect(m.lines).toEqual([]);
  });

  it('코드(pre)는 개행 기준 줄 배열', () => {
    const m = measure({ type: 'PRE', text: 'a\nb\nc' });
    expect(m.lines).toEqual(['a', 'b', 'c']);
    expect(m.lineHeight).toBeGreaterThan(0);
  });
});

describe('scaledStyle', () => {
  it('scale 이 폰트/줄높이/여백에 곱해진다', () => {
    const base = scaledStyle('P', 1);
    const scaled = scaledStyle('P', 2);
    expect(scaled.fontPx).toBeCloseTo(base.fontPx * 2);
    expect(scaled.lineHeight).toBeCloseTo(base.lineHeight * 2);
    expect(scaled.marginBottom).toBeCloseTo(base.marginBottom * 2);
  });

  it('미지정 타입은 P 로 폴백', () => {
    expect(blockStyle('UNKNOWN')).toEqual(blockStyle('P'));
  });
});

describe('PAGE_SIZES', () => {
  it('a4 프리셋 존재', () => {
    expect(PAGE_SIZES.a4.width).toBeGreaterThan(0);
    expect(PAGE_SIZES.a4.height).toBeGreaterThan(PAGE_SIZES.a4.width);
  });
});

// 인라인 세그먼트 파서 — 순수(canvas 불필요). 측정은 playwright 가 정본.
describe('parseInlineSegments', () => {
  it('평문은 서식 없는 단일 세그먼트', () => {
    const segs = parseInlineSegments('hello world');
    expect(segs).toEqual([{ text: 'hello world', bold: false, italic: false }]);
  });

  it('strong/em 을 bold/italic 로 표시', () => {
    const segs = parseInlineSegments('a<strong>b</strong><em>c</em>');
    expect(segs).toEqual([
      { text: 'a', bold: false, italic: false },
      { text: 'b', bold: true, italic: false },
      { text: 'c', bold: false, italic: true },
    ]);
  });

  it('b/i 도 strong/em 과 동일 취급', () => {
    const segs = parseInlineSegments('<b>x</b><i>y</i>');
    expect(segs).toEqual([
      { text: 'x', bold: true, italic: false },
      { text: 'y', bold: false, italic: true },
    ]);
  });

  it('중첩(strong>em)은 bold+italic 누적', () => {
    const segs = parseInlineSegments('<strong>bold <em>both</em></strong>');
    expect(segs).toEqual([
      { text: 'bold ', bold: true, italic: false },
      { text: 'both', bold: true, italic: true },
    ]);
  });

  it('u/a 는 서식 변화 없이 통과', () => {
    const segs = parseInlineSegments('<u>x</u><a href="/">y</a>');
    expect(segs).toEqual([{ text: 'xy', bold: false, italic: false }]);
  });

  it('인접 동일 서식은 병합', () => {
    const segs = parseInlineSegments('<strong>a</strong><strong>b</strong>');
    expect(segs).toEqual([{ text: 'ab', bold: true, italic: false }]);
  });

  it('<br> 은 강제개행 문자(\\n)로 세그먼트에 보존된다(#2)', () => {
    const segs = parseInlineSegments('a<br>b');
    // 같은 서식이라 하나로 병합되지만 \n 은 텍스트에 살아있어야 한다.
    expect(segs).toHaveLength(1);
    expect(segs[0].text).toBe('a\nb');
  });

  it('굵기 섞인 <br> 도 \\n 이 보존된다(#2)', () => {
    const segs = parseInlineSegments('a<br><strong>b</strong>');
    expect(segs.map((s) => s.text).join('')).toBe('a\nb');
    expect(segs.some((s) => s.bold)).toBe(true);
  });
});

// 표 모델 파서 — 순수(canvas 불필요).
describe('parseTableModel', () => {
  const parse = (html) => {
    const doc = new DOMParser().parseFromString(html, 'text/html');
    return parseTableModel(doc.querySelector('table'));
  };

  it('thead 를 헤더행으로, tbody 를 본문행으로 분리', () => {
    const model = parse(
      '<table><thead><tr><th>H1</th><th>H2</th></tr></thead>' +
        '<tbody><tr><td>a</td><td>b</td></tr><tr><td>c</td><td>d</td></tr></tbody></table>',
    );
    expect(model.headerRows).toHaveLength(1);
    expect(model.bodyRows).toHaveLength(2);
    expect(model.columnCount).toBe(2);
    expect(model.splittable).toBe(true);
    expect(model.headerRows[0].cells[0].header).toBe(true);
    expect(model.bodyRows[0].cells[0].text).toBe('a');
  });

  it('thead 없이 첫 행이 전부 th 면 헤더로 인식', () => {
    const model = parse(
      '<table><tr><th>H</th></tr><tr><td>x</td></tr></table>',
    );
    expect(model.headerRows).toHaveLength(1);
    expect(model.bodyRows).toHaveLength(1);
  });

  it('colspan 있으면 splittable=false (병합 표 분할 금지)', () => {
    const model = parse(
      '<table><tr><td colspan="2">merged</td></tr><tr><td>a</td><td>b</td></tr></table>',
    );
    expect(model.splittable).toBe(false);
    expect(model.columnCount).toBe(2);
  });

  it('rowspan 있으면 splittable=false', () => {
    const model = parse(
      '<table><tr><td rowspan="2">m</td><td>a</td></tr><tr><td>b</td></tr></table>',
    );
    expect(model.splittable).toBe(false);
  });

  it('셀 innerHTML 보존(인라인 서식)', () => {
    const model = parse('<table><tr><td><strong>bold</strong></td></tr></table>');
    expect(model.bodyRows[0].cells[0].html).toBe('<strong>bold</strong>');
  });

  it('중첩 표의 내부 행이 바깥 표에 섞이지 않는다(#3)', () => {
    // 바깥: 2열 1행. 내부 표는 셀 안에 3열 1행 — 바깥 열수/행수를 오염시키면 안 됨.
    const model = parse(
      '<table><thead><tr><th>A</th><th>B</th></tr></thead>' +
        '<tbody><tr><td>1</td>' +
        '<td><table><tr><td>x</td><td>y</td><td>z</td></tr></table></td>' +
        '</tr></tbody></table>',
    );
    expect(model.columnCount).toBe(2); // 내부 표의 3열이 새면 3
    expect(model.bodyRows).toHaveLength(1); // 내부 tr 이 새면 2
    expect(model.headerRows).toHaveLength(1);
  });
});
