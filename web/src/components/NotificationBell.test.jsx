import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import * as notifApi from '../services/api/notifications';
import { NotificationBell } from './NotificationBell';

vi.mock('../services/api/notifications');

const navigate = vi.fn();
vi.mock('react-router-dom', async (orig) => ({
  ...(await orig()),
  useNavigate: () => navigate,
}));

function renderBell() {
  return render(
    <MemoryRouter>
      <NotificationBell />
    </MemoryRouter>,
  );
}

describe('NotificationBell', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('안읽음이 있으면 배지 수를 보여준다', async () => {
    notifApi.getNotifications.mockResolvedValue({
      items: [{ id: 'n1', kind: 'NEW_BOOK', bookId: 'b1', title: '신간', isRead: false }],
      unreadCount: 1,
    });
    renderBell();
    expect(await screen.findByTestId('notif-badge')).toHaveTextContent('1');
  });

  it('항목 클릭 → 읽음 처리 + 책으로 이동', async () => {
    notifApi.getNotifications.mockResolvedValue({
      items: [{ id: 'n1', kind: 'NEW_BOOK', bookId: 'b1', title: '신간', isRead: false }],
      unreadCount: 1,
    });
    notifApi.markRead.mockResolvedValue(null);
    renderBell();

    fireEvent.click(await screen.findByTestId('notif-bell'));
    fireEvent.click(await screen.findByTestId('notif-item'));

    await waitFor(() => expect(notifApi.markRead).toHaveBeenCalledWith('n1'));
    expect(navigate).toHaveBeenCalledWith('/books/b1');
  });

  it('서평단 배정 알림을 배정 문구로 렌더한다', async () => {
    notifApi.getNotifications.mockResolvedValue({
      items: [{ id: 'n2', kind: 'ASSIGNED', bookId: 'b1', title: '밤의 편집자', isRead: false }],
      unreadCount: 1,
    });
    renderBell();
    fireEvent.click(await screen.findByTestId('notif-bell'));
    const item = await screen.findByTestId('notif-item');
    expect(item).toHaveTextContent('밤의 편집자');
    expect(item).toHaveTextContent('배정');
  });

  it('마감임박 알림을 마감 문구로 렌더한다', async () => {
    notifApi.getNotifications.mockResolvedValue({
      items: [{ id: 'n3', kind: 'DUE_SOON', bookId: 'b1', title: '밤의 편집자', isRead: false }],
      unreadCount: 1,
    });
    renderBell();
    fireEvent.click(await screen.findByTestId('notif-bell'));
    const item = await screen.findByTestId('notif-item');
    expect(item).toHaveTextContent('밤의 편집자');
    expect(item).toHaveTextContent('마감');
  });

  it('알림이 없으면 배지가 없다', async () => {
    notifApi.getNotifications.mockResolvedValue({ items: [], unreadCount: 0 });
    renderBell();
    await screen.findByTestId('notif-bell');
    expect(screen.queryByTestId('notif-badge')).not.toBeInTheDocument();
  });
});
