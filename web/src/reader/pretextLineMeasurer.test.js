// @vitest-environment node
// 실제 Pretext(@chenglou/pretext)에 대한 글루 테스트.
// jsdom 에는 canvas measureText 가 없어 node 환경 + @napi-rs/canvas 폴리필 사용.
// 이 테스트는 "line 객체의 .text 를 써야 한다"(start/end 는 객체라 slice 불가)를 잠근다.
import { beforeAll, describe, expect, it } from 'vitest';
import { createCanvas } from '@napi-rs/canvas';

beforeAll(() => {
  globalThis.OffscreenCanvas = class {
    constructor(w, h) {
      this._c = createCanvas(w || 1, h || 1);
    }
    getContext(t) {
      return this._c.getContext(t);
    }
  };
});

const { createPretextLineMeasurer } = await import('./pretextLineMeasurer');

describe('pretextLineMeasurer (real Pretext)', () => {
  it('줄 문자열을 .text 로 반환하고 비어있지 않다', () => {
    const measure = createPretextLineMeasurer({ contentWidth: 300, scale: 1 });
    const block = { type: 'P', html: '<p>' + '가나다라마바사 '.repeat(20) + '</p>' };

    const m = measure(block);

    expect(m.lines.length).toBeGreaterThan(1); // 여러 줄로 wrap
    expect(m.lines.every((l) => typeof l === 'string' && l.length > 0)).toBe(true);
    expect(m.lines.join('')).toContain('가나다라마바사');
  });

  it('HR 은 fixedHeight 로 처리(줄 측정 안 함)', () => {
    const measure = createPretextLineMeasurer({ contentWidth: 300, scale: 1 });
    const m = measure({ type: 'HR', html: '<hr/>' });
    expect(m.fixedHeight).toBeGreaterThan(0);
    expect(m.lines).toEqual([]);
  });
});
