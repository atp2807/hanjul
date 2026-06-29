import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

import * as campaigns from '../services/api/campaigns';
import * as studio from '../services/api/studio';
import { CampaignStudioPage } from './CampaignStudioPage';

vi.mock('../services/api/campaigns', async (o) => ({
  ...(await o()),
  getMyCampaigns: vi.fn(),
  getApplicants: vi.fn(),
  assignReviewer: vi.fn(),
  createCampaign: vi.fn(),
  closeCampaign: vi.fn(),
}));
vi.mock('../services/api/studio');
vi.mock('../auth/AuthContext', () => ({ useAuth: () => ({ user: { id: 'u1' } }) }));

function renderPage() {
  return render(<MemoryRouter><CampaignStudioPage /></MemoryRouter>);
}

describe('CampaignStudioPage', () => {
  it('집계 + 캠페인 행 + 신청자 배정', async () => {
    campaigns.getMyCampaigns.mockResolvedValue({ items: [
      { id: 'c1', bookId: 'b1', bookTitle: '관리책', slots: 10, filled: 3, remaining: 7, statusCd: 'OPEN', applicants: 5, reviewed: 2 },
    ] });
    studio.getMyBooks.mockResolvedValue({ items: [{ id: 'b1', title: '관리책', status: 'PUBLISHED' }] });
    campaigns.getApplicants.mockResolvedValue({ items: [
      { id: 'ap1', applicantId: 'u9', applicantName: '리뷰어A', statusCd: 'PENDING', deadlineAt: null },
    ] });
    campaigns.assignReviewer.mockResolvedValue(null);
    renderPage();

    expect(await screen.findByRole('heading', { name: '서평단 관리' })).toBeInTheDocument();
    expect(screen.getByText('관리책')).toBeInTheDocument();
    expect(screen.getByText('모집중')).toBeInTheDocument();
    expect(screen.getByText('5명')).toBeInTheDocument(); // 총 신청자 집계

    fireEvent.click(screen.getByRole('button', { name: '신청자' }));
    expect(await screen.findByText('리뷰어A')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '배정' }));
    await waitFor(() => expect(campaigns.assignReviewer).toHaveBeenCalledWith('c1', 'u9'));
  });

  it('진행중(OPEN) 캠페인을 작가가 마감한다', async () => {
    campaigns.getMyCampaigns.mockResolvedValue({ items: [
      { id: 'c1', bookId: 'b1', bookTitle: '마감대상', slots: 10, filled: 1, remaining: 9, statusCd: 'OPEN', applicants: 3, reviewed: 0 },
    ] });
    studio.getMyBooks.mockResolvedValue({ items: [] });
    campaigns.closeCampaign.mockResolvedValue(null);
    renderPage();

    fireEvent.click(await screen.findByRole('button', { name: '마감' }));
    await waitFor(() => expect(campaigns.closeCampaign).toHaveBeenCalledWith('c1'));
  });

  it('캠페인 없으면 빈 상태 안내', async () => {
    campaigns.getMyCampaigns.mockResolvedValue({ items: [] });
    studio.getMyBooks.mockResolvedValue({ items: [] });
    renderPage();
    expect(await screen.findByText('아직 캠페인이 없어요')).toBeInTheDocument();
  });
});
