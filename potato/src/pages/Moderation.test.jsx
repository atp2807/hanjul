import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('../api', () => ({
  api: { books: vi.fn(), takedown: vi.fn(), restore: vi.fn() },
}));

import { api } from '../api';
import Moderation from './Moderation';

const books = [
  { id: 'b1', title: '문제의 책', status: 'PUBLISHED', blocked: false },
  { id: 'b2', title: '차단된 책', status: 'PUBLISHED', blocked: true },
];

beforeEach(() => {
  vi.clearAllMocks();
  api.books.mockResolvedValue(books);
  api.takedown.mockResolvedValue({});
  api.restore.mockResolvedValue({});
});

describe('Moderation (운영자 모더레이션)', () => {
  it('책 목록을 보여주고 차단 여부에 따라 버튼이 다르다', async () => {
    render(<Moderation />);
    expect(await screen.findByText('문제의 책')).toBeInTheDocument();
    expect(screen.getByText('차단됨')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '강제 비공개' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '복원' })).toBeInTheDocument();
  });

  it('강제 비공개는 사유 프롬프트를 받아 takedown을 호출한다', async () => {
    vi.spyOn(window, 'prompt').mockReturnValue('저작권 침해');
    render(<Moderation />);
    fireEvent.click(await screen.findByRole('button', { name: '강제 비공개' }));
    await waitFor(() => expect(api.takedown).toHaveBeenCalledWith('b1', '저작권 침해'));
  });

  it('프롬프트 취소(null) 시 takedown하지 않는다', async () => {
    vi.spyOn(window, 'prompt').mockReturnValue(null);
    render(<Moderation />);
    fireEvent.click(await screen.findByRole('button', { name: '강제 비공개' }));
    expect(api.takedown).not.toHaveBeenCalled();
  });

  it('복원은 restore를 호출한다', async () => {
    render(<Moderation />);
    fireEvent.click(await screen.findByRole('button', { name: '복원' }));
    await waitFor(() => expect(api.restore).toHaveBeenCalledWith('b2'));
  });

  it('빈 목록이면 안내를 보여준다', async () => {
    api.books.mockResolvedValue([]);
    render(<Moderation />);
    expect(await screen.findByText('책이 없습니다.')).toBeInTheDocument();
  });
});
