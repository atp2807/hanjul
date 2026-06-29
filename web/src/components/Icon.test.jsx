import { render } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { Icon } from './Icon';

describe('Icon', () => {
  it('이름별로 svg를 렌더한다', () => {
    const { container } = render(<Icon name="search" />);
    expect(container.querySelector('svg')).toBeTruthy();
  });

  it('stroke 색을 적용한다', () => {
    const { container } = render(<Icon name="bell" stroke="#0e4a5c" />);
    expect(container.querySelector('svg').getAttribute('stroke')).toBe('#0e4a5c');
  });

  it('모르는 이름이면 아무것도 안 그린다(안전)', () => {
    const { container } = render(<Icon name="없는아이콘" />);
    expect(container.querySelector('svg')).toBeNull();
  });
});
