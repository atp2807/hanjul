import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

// 조판 엔진은 canvas 측정 의존(jsdom 미지원) → UI 테스트용으로 2페이지 고정 목킹
vi.mock('./pretextLineMeasurer', () => ({ createPretextLineMeasurer: () => () => [] }));
vi.mock('./paginateLines', () => ({
  paginateLines: () => [
    [{ blockId: 'b1', type: 'H1', lines: ['1장'] }],
    [{ blockId: 'b2', type: 'P', lines: ['본문'] }],
  ],
}));

import { Reader } from './Reader';

const BLOCKS = [
  { blockId: 'b1', type: 'H1', html: '<h1>1장</h1>' },
  { blockId: 'b2', type: 'P', html: '<p>본문 한 줄.</p>' },
];

describe('Reader 설정 영속', () => {
  beforeEach(() => localStorage.clear());

  it('테마 선택 → localStorage 저장 + 배경색 반영', () => {
    render(<Reader blocks={BLOCKS} bookId="bk1" />);
    fireEvent.click(screen.getByTestId('theme-dark'));
    expect(localStorage.getItem('hanjul-reader-theme')).toBe('dark');
    expect(screen.getByTestId('theme-dark')).toHaveAttribute('aria-pressed', 'true');
  });

  it('저장된 테마/배율을 다시 열 때 복원', () => {
    localStorage.setItem('hanjul-reader-theme', 'sepia');
    localStorage.setItem('hanjul-reader-scale', '1.3');
    render(<Reader blocks={BLOCKS} bookId="bk1" />);
    expect(screen.getByTestId('theme-sepia')).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByText(/배율 1\.3x/)).toBeInTheDocument();
  });

  it('다음 페이지 → 책별 위치 저장(이어보기)', () => {
    render(<Reader blocks={BLOCKS} bookId="bk1" />);
    fireEvent.click(screen.getByRole('button', { name: /다음/ }));
    expect(localStorage.getItem('hanjul-reader-pos-bk1')).toBe('1');
  });

  it('저장된 위치에서 재개', () => {
    localStorage.setItem('hanjul-reader-pos-bk1', '1');
    render(<Reader blocks={BLOCKS} bookId="bk1" />);
    expect(screen.getByText('2 / 2')).toBeInTheDocument(); // 2페이지째부터
  });
});
