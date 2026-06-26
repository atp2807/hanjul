import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

import * as authCtx from '../auth/AuthContext';
import { Header } from './Header';

vi.mock('../auth/AuthContext');
vi.mock('../services/api/notifications', () => ({
  getNotifications: vi.fn().mockResolvedValue({ items: [], unreadCount: 0 }),
  markRead: vi.fn(),
  markAllRead: vi.fn(),
}));

function renderHeader() {
  return render(
    <MemoryRouter>
      <Header />
    </MemoryRouter>,
  );
}

describe('Header', () => {
  it('미로그인: 로그인 + 무료로 시작', () => {
    authCtx.useAuth.mockReturnValue({ user: null, logout: vi.fn() });
    renderHeader();
    expect(screen.getByText('무료로 시작')).toBeInTheDocument();
    expect(screen.getByText('로그인')).toBeInTheDocument();
  });

  it('로그인: 이름 + 내서재/로그아웃', () => {
    authCtx.useAuth.mockReturnValue({ user: { displayName: '박작가', email: 'a@x.com' }, logout: vi.fn() });
    renderHeader();
    expect(screen.getByText('박작가')).toBeInTheDocument();
    expect(screen.getByText('내 서재')).toBeInTheDocument();
    expect(screen.getByText('로그아웃')).toBeInTheDocument();
  });
});
