import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

import * as authors from '../services/api/authors';
import * as notifications from '../services/api/notifications';
import { AuthorPage } from './AuthorPage';

vi.mock('../services/api/authors', async (o) => ({ ...(await o()), getAuthor: vi.fn() }));
vi.mock('../services/api/notifications', async (o) => ({
  ...(await o()),
  getFollowStatus: vi.fn(),
  followAuthor: vi.fn(),
  unfollowAuthor: vi.fn(),
}));

let mockUser = { id: 'u1' };
vi.mock('../auth/AuthContext', () => ({ useAuth: () => ({ user: mockUser }) }));

const AUTHOR = {
  id: 'a1',
  displayName: '박작가',
  bio: '한 줄 소개\n둘째 줄',
  books: [{ id: 'b1', title: '밤의 편집자', coverUrl: null, priceAmt: 9900 }],
};

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/authors/a1']}>
      <Routes><Route path="/authors/:id" element={<AuthorPage />} /></Routes>
    </MemoryRouter>,
  );
}

describe('AuthorPage', () => {
  it('작가 프로필 + 작품 목록 렌더', async () => {
    authors.getAuthor.mockResolvedValue(AUTHOR);
    notifications.getFollowStatus.mockResolvedValue({ following: false });
    renderPage();

    expect(await screen.findByTestId('author-name')).toHaveTextContent('박작가');
    expect(screen.getByTestId('author-bio')).toHaveTextContent('한 줄 소개');
    expect(screen.getByTestId('author-books')).toHaveTextContent('밤의 편집자');
    expect(screen.getByText('9,900원')).toBeInTheDocument();
  });

  it('작가를 찾을 수 없으면 404 안내 (일반 에러와 구분)', async () => {
    const err = new Error('not found'); err.status = 404;
    authors.getAuthor.mockRejectedValue(err);
    renderPage();
    expect(await screen.findByText('작가를 찾을 수 없어요.')).toBeInTheDocument();
  });

  it('일시 장애는 원문 메시지 표시 (404 문구로 뭉뚱그리지 않기)', async () => {
    authors.getAuthor.mockRejectedValue(new Error('network down'));
    renderPage();
    expect(await screen.findByText('network down')).toBeInTheDocument();
  });

  it('본인 페이지에는 팔로우 버튼 없음', async () => {
    mockUser = { id: 'a1' };
    authors.getAuthor.mockResolvedValue(AUTHOR);
    renderPage();
    await screen.findByTestId('author-name');
    expect(screen.queryByTestId('follow-btn')).not.toBeInTheDocument();
    mockUser = { id: 'u1' };
  });

  it('팔로우 토글 성공 → 라벨 전환', async () => {
    authors.getAuthor.mockResolvedValue(AUTHOR);
    notifications.getFollowStatus.mockResolvedValue({ following: false });
    notifications.followAuthor.mockResolvedValue(null);
    renderPage();

    const btn = await screen.findByTestId('follow-btn');
    expect(btn).toHaveTextContent('＋ 팔로우');
    fireEvent.click(btn);
    await waitFor(() => expect(notifications.followAuthor).toHaveBeenCalledWith('a1'));
    expect(await screen.findByText('팔로잉')).toBeInTheDocument();
  });

  it('팔로우 토글 실패 → 무반응 아니라 에러 안내 (서버 detail 우선)', async () => {
    authors.getAuthor.mockResolvedValue(AUTHOR);
    notifications.getFollowStatus.mockResolvedValue({ following: false });
    const err = new Error('x'); err.detail = '팔로우할 수 없는 작가예요.';
    notifications.followAuthor.mockRejectedValue(err);
    renderPage();

    fireEvent.click(await screen.findByTestId('follow-btn'));
    expect(await screen.findByText('팔로우할 수 없는 작가예요.')).toBeInTheDocument();
    // 실패했으니 라벨은 그대로 유지
    expect(screen.getByTestId('follow-btn')).toHaveTextContent('＋ 팔로우');
  });

  it('팔로우 상태 확인 실패 → 미팔로우로 표시(침묵 허용)', async () => {
    authors.getAuthor.mockResolvedValue(AUTHOR);
    notifications.getFollowStatus.mockRejectedValue(new Error('boom'));
    renderPage();
    expect(await screen.findByTestId('follow-btn')).toHaveTextContent('＋ 팔로우');
  });
});
