import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

import * as notifApi from '../services/api/notifications';
import { NotificationsPage } from './NotificationsPage';

vi.mock('../services/api/notifications');
vi.mock('../auth/AuthContext', () => ({ useAuth: () => ({ user: { id: 'u1' } }) }));

const navigate = vi.fn();
vi.mock('react-router-dom', async (orig) => ({ ...(await orig()), useNavigate: () => navigate }));

function renderPage() {
  return render(<MemoryRouter><NotificationsPage /></MemoryRouter>);
}

describe('NotificationsPage', () => {
  it('알림 목록을 종류별 문구로 렌더한다', async () => {
    notifApi.getNotifications.mockResolvedValue({
      items: [
        { id: 'n1', kind: 'ASSIGNED', bookId: 'b1', title: '밤의 편집자', isRead: false },
        { id: 'n2', kind: 'DUE_SOON', bookId: 'b2', title: '새벽의 문장', isRead: true },
      ],
      unreadCount: 1,
    });
    renderPage();
    expect(await screen.findByText('밤의 편집자')).toBeInTheDocument();
    expect(screen.getByText('새벽의 문장')).toBeInTheDocument();
    expect(screen.getByText(/배정/)).toBeInTheDocument(); // ASSIGNED 메시지
    expect(screen.getAllByText(/마감/).length).toBeGreaterThanOrEqual(1); // DUE_SOON 메시지/라벨
  });

  it('모두 읽음 → markAllRead 호출', async () => {
    notifApi.getNotifications.mockResolvedValue({
      items: [{ id: 'n1', kind: 'ASSIGNED', bookId: 'b1', title: '밤의 편집자', isRead: false }],
      unreadCount: 1,
    });
    notifApi.markAllRead.mockResolvedValue(null);
    renderPage();
    fireEvent.click(await screen.findByRole('button', { name: '모두 읽음' }));
    await waitFor(() => expect(notifApi.markAllRead).toHaveBeenCalled());
  });

  it('항목 클릭 → 읽음 처리 + 책으로 이동', async () => {
    notifApi.getNotifications.mockResolvedValue({
      items: [{ id: 'n1', kind: 'ASSIGNED', bookId: 'b1', title: '밤의 편집자', isRead: false }],
      unreadCount: 1,
    });
    notifApi.markRead.mockResolvedValue(null);
    renderPage();
    fireEvent.click(await screen.findByTestId('notif-row'));
    await waitFor(() => expect(notifApi.markRead).toHaveBeenCalledWith('n1'));
    expect(navigate).toHaveBeenCalledWith('/books/b1');
  });

  it('알림이 없으면 빈 상태', async () => {
    notifApi.getNotifications.mockResolvedValue({ items: [], unreadCount: 0 });
    renderPage();
    expect(await screen.findByText(/알림이 없어요/)).toBeInTheDocument();
  });
});
