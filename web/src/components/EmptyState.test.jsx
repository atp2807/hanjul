import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { EmptyState } from './EmptyState';

describe('EmptyState', () => {
  it('아이콘 + 제목 + 설명을 렌더한다', () => {
    render(<EmptyState icon="search" title="없어요" desc="곧 표시돼요" />);
    expect(screen.getByText('없어요')).toBeInTheDocument();
    expect(screen.getByText('곧 표시돼요')).toBeInTheDocument();
    expect(screen.getByTestId('icon')).toBeInTheDocument(); // aria-hidden 장식 아이콘 — testid로 지정
  });

  it('action 있으면 버튼 클릭이 동작한다', () => {
    const onClick = vi.fn();
    render(<EmptyState title="비었음" action={{ label: '둘러보기', onClick }} />);
    fireEvent.click(screen.getByRole('button', { name: '둘러보기' }));
    expect(onClick).toHaveBeenCalled();
  });
});
