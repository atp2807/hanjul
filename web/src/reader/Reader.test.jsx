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

// 주의: Reader가 받는 원본 blocks는 필드명이 `id`(paginateLines.js가 frag.blockId = block.id로 파생).
// `blockId`로 잘못 두면 tocFromBlocks()의 키가 undefined가 돼(React "missing key" 경고) 목차 클릭도
// 무동작이 된다 — 그동안 목차 드롭다운을 여는 테스트가 없어서 못 잡았던 픽스처 버그.
const BLOCKS = [
  { id: 'b1', type: 'H1', html: '<h1>1장</h1>' },
  { id: 'b2', type: 'P', html: '<p>본문 한 줄.</p>' },
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

// lr-ca34f579 ② 커스텀 드롭다운(목차) 키보드 접근성 — 열릴 때 포커스 이동, Esc로 닫기, 트리거로 포커스 리턴
describe('Reader 목차 드롭다운 키보드 접근성', () => {
  beforeEach(() => localStorage.clear());

  it('열면 목차 안으로 포커스가 이동한다', () => {
    render(<Reader blocks={BLOCKS} bookId="bk1" />);
    fireEvent.click(screen.getByTestId('toc-toggle'));
    // 목차 안 첫 포커스 가능 요소(첫 장 항목 "1장")로 이동했는지 확인
    expect(screen.getByRole('button', { name: '1장' })).toHaveFocus();
  });

  it('Esc로 닫히고 포커스가 목차 버튼으로 되돌아온다', () => {
    render(<Reader blocks={BLOCKS} bookId="bk1" />);
    const toggle = screen.getByTestId('toc-toggle');
    // jsdom fireEvent.click은 실브라우저의 클릭-시-포커스를 재현하지 않으므로 명시적으로 포커스
    toggle.focus();
    fireEvent.click(toggle);
    expect(screen.getByTestId('toc-list')).toBeInTheDocument();

    fireEvent.keyDown(document, { key: 'Escape' });

    expect(screen.queryByTestId('toc-list')).not.toBeInTheDocument();
    expect(toggle).toHaveFocus();
  });
});
