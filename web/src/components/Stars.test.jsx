import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { Stars } from './Stars';

describe('Stars', () => {
  it('표시 모드 — max개 별 렌더', () => {
    render(<Stars value={3} max={5} />);
    expect(screen.getAllByTestId('icon')).toHaveLength(5); // aria-hidden 장식 별 아이콘 — testid로 개수 확인
  });

  it('입력 모드 — 별 클릭 시 onRate(n)', () => {
    const onRate = vi.fn();
    render(<Stars value={0} onRate={onRate} />);
    fireEvent.click(screen.getByRole('button', { name: '별점 5점' }));
    expect(onRate).toHaveBeenCalledWith(5);
  });
});
