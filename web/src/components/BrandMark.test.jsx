import { render } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { BrandMark } from './BrandMark';

describe('BrandMark', () => {
  it('스쿼클 + 3줄 SVG 마크를 렌더한다', () => {
    const { container } = render(<BrandMark size={32} />);
    const svg = container.querySelector('svg');
    expect(svg).toBeTruthy();
    // 강조된 가운데 한 줄(긴 rect) + 보조 줄/점 = rect 2 + circle 1
    expect(container.querySelectorAll('rect').length).toBe(2);
    expect(container.querySelector('circle')).toBeTruthy();
  });
});
