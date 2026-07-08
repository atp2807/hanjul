import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

// 조판 엔진은 canvas 측정 의존(jsdom 미지원) → Reader.test.jsx와 동일하게 목킹
vi.mock('../reader/pretextLineMeasurer', () => ({ createPretextLineMeasurer: () => () => [] }));
vi.mock('../reader/paginateLines', () => ({
  paginateLines: () => [[{ blockId: 'b1', type: 'P', lines: ['본문'] }]],
}));

import { PreviewModal } from './PreviewModal';

const BLOCKS = [{ blockId: 'b1', type: 'P', html: '<p>본문 한 줄.</p>' }];

// lr-ca34f579 ② 실제 배경을 덮는 블로킹 모달 — 4가지 키보드 접근성 전부 검증
describe('PreviewModal 키보드 접근성', () => {
  it('role=dialog + aria-modal + 열리면 안으로 포커스 이동(닫기 버튼)', () => {
    render(<PreviewModal blocks={BLOCKS} onClose={vi.fn()} />);
    const dialog = screen.getByRole('dialog', { name: '출판 전 미리보기 (독자가 볼 모습)' });
    expect(dialog).toHaveAttribute('aria-modal', 'true');
    expect(screen.getByRole('button', { name: '닫기' })).toHaveFocus();
  });

  it('Esc → onClose 호출', () => {
    const onClose = vi.fn();
    render(<PreviewModal blocks={BLOCKS} onClose={onClose} />);
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('배경(오버레이) 클릭 → onClose 호출, 모달 내부 클릭은 안 닫힘', () => {
    const onClose = vi.fn();
    render(<PreviewModal blocks={BLOCKS} onClose={onClose} />);
    fireEvent.click(screen.getByTestId('preview-body'));
    expect(onClose).not.toHaveBeenCalled();
    fireEvent.click(screen.getByTestId('preview-overlay'));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('닫히면(언마운트) 트리거로 포커스가 되돌아온다', () => {
    // 트리거 버튼을 먼저 렌더+포커스해 둔 뒤 모달을 마운트 → 언마운트 시 포커스 리턴을 확인
    render(<button>열기</button>);
    const trigger = screen.getByRole('button', { name: '열기' });
    trigger.focus();
    expect(trigger).toHaveFocus();

    const { unmount } = render(<PreviewModal blocks={BLOCKS} onClose={vi.fn()} />);
    expect(screen.getByRole('button', { name: '닫기' })).toHaveFocus();

    unmount();
    expect(trigger).toHaveFocus();
  });
});
