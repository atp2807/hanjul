import { describe, expect, it } from 'vitest';

import { paginate } from './paginate';

// 가짜 measure — 블록 height 를 block.h 로 직접 지정 (Pretext/캔버스 불필요).
const measure = (block) => block.h;
const mk = (n, h) => Array.from({ length: n }, (_, i) => ({ id: `b${i}`, h }));

describe('paginate', () => {
  it('빈 입력 → 0 페이지', () => {
    expect(paginate([], { contentHeight: 100, measure })).toEqual([]);
  });

  it('합이 페이지보다 작으면 1 페이지', () => {
    const pages = paginate(mk(3, 20), { contentHeight: 100, measure });
    expect(pages).toHaveLength(1);
    expect(pages[0]).toHaveLength(3);
  });

  it('초과하면 다음 페이지로 분할', () => {
    // 20px 블록 5개, 페이지 60px → 3+? : [3],[2] => 2페이지 (60에 3개=60 OK, 4번째서 분할)
    const pages = paginate(mk(5, 20), { contentHeight: 60, measure });
    expect(pages).toHaveLength(2);
    expect(pages[0]).toHaveLength(3);
    expect(pages[1]).toHaveLength(2);
  });

  it('페이지가 작을수록 페이지 수가 늘어난다 (단조성)', () => {
    const blocks = mk(10, 20);
    const few = paginate(blocks, { contentHeight: 200, measure });
    const many = paginate(blocks, { contentHeight: 40, measure });
    expect(many.length).toBeGreaterThan(few.length);
  });

  it('폰트가 커지면(블록 높이↑) 페이지 수가 늘어난다 — 재조판', () => {
    const small = paginate(mk(8, 20), { contentHeight: 100, measure });
    const large = paginate(mk(8, 40), { contentHeight: 100, measure });
    expect(large.length).toBeGreaterThan(small.length);
  });

  it('페이지보다 큰 단일 블록은 단독 배치(무한루프 없음)', () => {
    const pages = paginate(
      [{ id: 'big', h: 500 }, { id: 'small', h: 10 }],
      { contentHeight: 100, measure },
    );
    expect(pages).toHaveLength(2);
    expect(pages[0]).toEqual([{ id: 'big', h: 500 }]);
  });

  it('모든 블록이 정확히 한 번씩 등장한다 (유실 없음)', () => {
    const blocks = mk(7, 30);
    const pages = paginate(blocks, { contentHeight: 100, measure });
    const flat = pages.flat();
    expect(flat).toHaveLength(7);
    expect(flat.map((b) => b.id)).toEqual(blocks.map((b) => b.id));
  });
});
