import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { BrandMark } from './BrandMark';

describe('BrandMark', () => {
  it('스쿼클 + 3줄 SVG 마크를 렌더한다', () => {
    render(<BrandMark size={32} />);
    const svg = screen.getByTestId('brandmark-svg'); // aria-hidden 장식 svg — testid로 지정
    // 강조된 가운데 한 줄(긴 rect) + 보조 줄/점 = rect 2 + circle 1.
    // 순수 시각 구성(색·역할 없는 도형 개수) 확인이라 RTL 접근성 쿼리로 표현 불가 —
    // querySelector 잔존은 의도적(testing-library/no-node-access 불가피 케이스).
    expect(svg.querySelectorAll('rect').length).toBe(2);
    expect(svg.querySelector('circle')).toBeTruthy();
  });
});
