import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('../api', () => ({
  api: { reviewQueue: vi.fn(), takedown: vi.fn() },
}));

import { api } from '../api';
import ReviewQueue from './ReviewQueue';

const items = [
  {
    bookId: 'b1', title: '성인 웹소설', authorId: 'a1', rating: 'AGE18',
    reasons: ['AGE18'], publishedAt: '2026-07-01T00:00:00Z',
  },
  {
    bookId: 'b2', title: '신고된 책', authorId: 'a2', rating: 'ALL',
    reasons: ['REPORTED'], publishedAt: '2026-07-02T00:00:00Z',
  },
];

beforeEach(() => {
  vi.clearAllMocks();
  api.reviewQueue.mockResolvedValue(items);
  api.takedown.mockResolvedValue(null);
});

describe('ReviewQueue (운영자 검토 큐)', () => {
  it('책 목록을 등급·이유 배지와 함께 보여준다', async () => {
    render(<ReviewQueue />);
    expect(await screen.findByText('성인 웹소설')).toBeInTheDocument();
    expect(screen.getByText('연령')).toBeInTheDocument();
    expect(screen.getByText('신고된 책')).toBeInTheDocument();
    expect(screen.getByText('신고')).toBeInTheDocument();
  });

  it('내리기 버튼은 사유 프롬프트를 받아 takedown을 호출하고 목록을 다시 불러온다', async () => {
    vi.spyOn(window, 'prompt').mockReturnValue('연령 표기 누락');
    render(<ReviewQueue />);
    const buttons = await screen.findAllByRole('button', { name: '내리기' });
    fireEvent.click(buttons[0]);
    await waitFor(() => expect(api.takedown).toHaveBeenCalledWith('b1', '연령 표기 누락'));
    await waitFor(() => expect(api.reviewQueue.mock.calls.length).toBeGreaterThanOrEqual(2));
  });

  it('프롬프트 취소(null) 시 takedown하지 않는다', async () => {
    vi.spyOn(window, 'prompt').mockReturnValue(null);
    render(<ReviewQueue />);
    const buttons = await screen.findAllByRole('button', { name: '내리기' });
    fireEvent.click(buttons[0]);
    expect(api.takedown).not.toHaveBeenCalled();
  });

  it('빈 목록이면 안내를 보여준다', async () => {
    api.reviewQueue.mockResolvedValue([]);
    render(<ReviewQueue />);
    expect(await screen.findByText('검토가 필요한 책이 없습니다.')).toBeInTheDocument();
  });
});
