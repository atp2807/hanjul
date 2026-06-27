import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

import * as campaigns from '../services/api/campaigns';
import { ReviewerActivityPage } from './ReviewerActivityPage';

vi.mock('../services/api/campaigns', async (o) => ({
  ...(await o()),
  getMyApplications: vi.fn(),
  getReviewerStatus: vi.fn(),
  cancelApplication: vi.fn(),
}));
vi.mock('../auth/AuthContext', () => ({ useAuth: () => ({ user: { id: 'u1' } }) }));

const APPS = [
  { id: 'a1', campaignId: 'c1', bookId: 'b1', bookTitle: '배정책', statusCd: 'ASSIGNED', deadlineAt: '2099-01-01T00:00:00Z' },
  { id: 'a2', campaignId: 'c2', bookId: 'b2', bookTitle: '대기책', statusCd: 'PENDING', deadlineAt: null },
  { id: 'a3', campaignId: 'c3', bookId: 'b3', bookTitle: '만료책', statusCd: 'EXPIRED', deadlineAt: null },
  { id: 'a4', campaignId: 'c4', bookId: 'b4', bookTitle: '완료책', statusCd: 'COMPLETED', deadlineAt: null },
];

function renderPage() {
  return render(<MemoryRouter><ReviewerActivityPage /></MemoryRouter>);
}

describe('ReviewerActivityPage', () => {
  it('상태별 신청 + 완료율 + 신청취소', async () => {
    campaigns.getMyApplications.mockResolvedValue({ items: APPS });
    campaigns.getReviewerStatus.mockResolvedValue({ completed: 1, missed: 1, active: 1, pending: 1, received: 3, completionRate: 50, blockedUntil: null });
    campaigns.cancelApplication.mockResolvedValue(null);
    renderPage();

    expect(await screen.findByText('배정책')).toBeInTheDocument();
    expect(screen.getByText('배정됨')).toBeInTheDocument();
    expect(screen.getByText('기한 초과')).toBeInTheDocument(); // EXPIRED 배지
    expect(screen.getByText('기한 종료')).toBeInTheDocument(); // EXPIRED 액션
    expect(screen.getByText('50%')).toBeInTheDocument(); // 완료율(서버 집계)

    fireEvent.click(screen.getByRole('button', { name: '신청 취소' }));
    await waitFor(() => expect(campaigns.cancelApplication).toHaveBeenCalledWith('c2'));
  });

  it('자격회수 중이면 배너 + 자격 회수 표시', async () => {
    campaigns.getMyApplications.mockResolvedValue({ items: [] });
    campaigns.getReviewerStatus.mockResolvedValue({ completed: 0, missed: 2, active: 0, pending: 0, received: 2, completionRate: 0, blockedUntil: '2099-06-01T00:00:00Z' });
    renderPage();

    expect(await screen.findByText(/서평단 자격이 회수/)).toBeInTheDocument();
    expect(screen.getByText('회수')).toBeInTheDocument(); // 자격 카드 값
  });
});
