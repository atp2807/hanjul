import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { Icon } from './Icon';

// Icon은 aria-hidden 순수 장식 svg — 접근성 트리에 role/name이 없어 getByRole 등으로
// 지정 불가. data-testid는 이런 케이스를 위해 RTL이 공식 권장하는 최종수단 쿼리.
describe('Icon', () => {
  it('이름별로 svg를 렌더한다', () => {
    render(<Icon name="search" />);
    expect(screen.getByTestId('icon')).toBeInTheDocument();
  });

  it('stroke 색을 적용한다', () => {
    render(<Icon name="bell" stroke="#0e4a5c" />);
    expect(screen.getByTestId('icon')).toHaveAttribute('stroke', '#0e4a5c');
  });

  it('모르는 이름이면 아무것도 안 그린다(안전)', () => {
    render(<Icon name="없는아이콘" />);
    expect(screen.queryByTestId('icon')).not.toBeInTheDocument();
  });
});
