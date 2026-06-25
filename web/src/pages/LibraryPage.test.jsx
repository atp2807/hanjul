import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

import * as authCtx from '../auth/AuthContext';
import * as orders from '../services/api/orders';
import { LibraryPage } from './LibraryPage';

vi.mock('../auth/AuthContext');
vi.mock('../services/api/orders');

function renderLib() {
  return render(
    <MemoryRouter>
      <LibraryPage />
    </MemoryRouter>,
  );
}

describe('LibraryPage', () => {
  it('미로그인이면 로그인 안내', async () => {
    authCtx.useAuth.mockReturnValue({ user: null, loading: false });
    renderLib();
    expect(await screen.findByText(/로그인이 필요해요/)).toBeInTheDocument();
  });

  it('구매한 책 목록을 렌더한다', async () => {
    authCtx.useAuth.mockReturnValue({ user: { id: '1' }, loading: false });
    orders.getLibrary.mockResolvedValue([{ bookId: 'b1', title: '산 책', coverUrl: null }]);
    renderLib();
    // 표지 플레이스홀더에도 제목 → findAllBy
    expect((await screen.findAllByText('산 책')).length).toBeGreaterThanOrEqual(1);
  });

  it('빈 서재 안내', async () => {
    authCtx.useAuth.mockReturnValue({ user: { id: '1' }, loading: false });
    orders.getLibrary.mockResolvedValue([]);
    renderLib();
    expect(await screen.findByText(/아직 구매한 책이 없어요/)).toBeInTheDocument();
  });

  it('환불 → confirm 후 refundOrder 호출 + 목록에서 제거', async () => {
    authCtx.useAuth.mockReturnValue({ user: { id: '1' }, loading: false });
    orders.getLibrary.mockResolvedValue([{ bookId: 'b1', title: '환불할 책', coverUrl: null, orderId: 'o1' }]);
    orders.refundOrder.mockResolvedValue(null);
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    renderLib();

    fireEvent.click(await screen.findByText('환불'));
    await waitFor(() => expect(orders.refundOrder).toHaveBeenCalledWith('o1'));
    await waitFor(() => expect(screen.getByText(/아직 구매한 책이 없어요/)).toBeInTheDocument());
  });
});
