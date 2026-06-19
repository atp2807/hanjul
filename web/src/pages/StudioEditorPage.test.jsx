import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import * as books from '../services/api/books';
import * as studio from '../services/api/studio';
import { StudioEditorPage } from './StudioEditorPage';

vi.mock('../services/api/books');
vi.mock('../services/api/studio');

function renderEditor() {
  return render(
    <MemoryRouter initialEntries={['/studio/b1']}>
      <Routes>
        <Route path="/studio/:id" element={<StudioEditorPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  studio.getMyBooks.mockResolvedValue({ items: [{ id: 'b1', isbn: '9788912345678' }] });
});

describe('StudioEditorPage', () => {
  it('초안: ISBN·즉시출간·예약발행을 노출하고 배포 섹션은 숨긴다', async () => {
    books.getBookContent.mockResolvedValue({
      id: 'b1', title: '내 책', status: 'DRAFT', priceAmt: 9000, chapters: [],
    });
    renderEditor();
    expect(await screen.findByText('내 책')).toBeInTheDocument();
    expect(screen.getByDisplayValue('9788912345678')).toBeInTheDocument(); // ISBN 로드
    expect(screen.getByText('즉시 출간')).toBeInTheDocument();
    expect(screen.getByText('예약 발행')).toBeInTheDocument();
    expect(screen.queryByText('서점 배포')).not.toBeInTheDocument(); // 미출판
  });

  it('출판본: 서점 배포 → 전송됨 이력이 다시 로드된다', async () => {
    books.getBookContent.mockResolvedValue({
      id: 'b1', title: '내 책', status: 'PUBLISHED', priceAmt: 9000, chapters: [],
    });
    studio.getDistributions
      .mockResolvedValueOnce([])
      .mockResolvedValue([
        { id: 'd1', channelCd: 'KYOBO', statusCd: 'SENT', message: null, createdAt: '2026-06-18T00:00:00Z' },
      ]);
    studio.distributeBook.mockResolvedValue({ statusCd: 'SENT', channelCd: 'KYOBO' });

    renderEditor();
    fireEvent.click(await screen.findByText('배포 전송'));

    await waitFor(() => expect(studio.distributeBook).toHaveBeenCalledWith('b1', 'KYOBO'));
    expect(await screen.findByText('전송됨')).toBeInTheDocument();
  });
});
