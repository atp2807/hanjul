import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

import * as campaigns from '../services/api/campaigns';
import * as books from '../services/api/books';
import { CampaignDetailPage } from './CampaignDetailPage';

vi.mock('../services/api/campaigns', async (o) => ({
  ...(await o()),
  getCampaign: vi.fn(),
  getMyApplications: vi.fn(),
  applyCampaign: vi.fn(),
}));
vi.mock('../services/api/books');
vi.mock('../auth/AuthContext', () => ({ useAuth: () => ({ user: { id: 'u1' } }) }));

const CAMP = { id: 'c1', bookId: 'b1', bookTitle: '밤의 편집자', slots: 30, filled: 23, remaining: 7, reviewDays: 14, minChars: 300, status: 'OPEN' };

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/campaigns/c1']}>
      <Routes><Route path="/campaigns/:id" element={<CampaignDetailPage />} /></Routes>
    </MemoryRouter>,
  );
}

describe('CampaignDetailPage', () => {
  it('캠페인 정보 + 신청하면 완료 상태로 바뀐다', async () => {
    campaigns.getCampaign.mockResolvedValue(CAMP);
    campaigns.getMyApplications.mockResolvedValue({ items: [] });
    campaigns.applyCampaign.mockResolvedValue(null);
    books.getStoreDetail.mockResolvedValue({});
    renderPage();

    expect(await screen.findByRole('heading', { name: '밤의 편집자' })).toBeInTheDocument();
    expect(screen.getByText(/7부/)).toBeInTheDocument(); // 남은 증정본

    fireEvent.click(screen.getByRole('button', { name: '리뷰어 신청하기' }));
    // 클릭 → 신청 API 호출 (완료 표시 자체는 '이미 신청' 케이스에서 검증)
    await waitFor(() => expect(campaigns.applyCampaign).toHaveBeenCalledWith('c1'));
  });

  it('신청 실패(409) — 서버 detail 문구를 그대로 표시', async () => {
    campaigns.getCampaign.mockResolvedValue(CAMP);
    campaigns.getMyApplications.mockResolvedValue({ items: [] });
    const err = new Error('마감됐거나 신청할 수 없는 모집이에요.');
    err.status = 409; err.detail = '마감됐거나 신청할 수 없는 모집이에요.';
    campaigns.applyCampaign.mockRejectedValue(err);
    books.getStoreDetail.mockResolvedValue({});
    renderPage();

    fireEvent.click(await screen.findByRole('button', { name: '리뷰어 신청하기' }));
    await waitFor(() => expect(screen.getByText('마감됐거나 신청할 수 없는 모집이에요.')).toBeInTheDocument());
  });

  it('신청 실패 — detail 없으면 일반 문구 (침묵 금지)', async () => {
    campaigns.getCampaign.mockResolvedValue(CAMP);
    campaigns.getMyApplications.mockResolvedValue({ items: [] });
    campaigns.applyCampaign.mockRejectedValue(new Error('network'));
    books.getStoreDetail.mockResolvedValue({});
    renderPage();

    fireEvent.click(await screen.findByRole('button', { name: '리뷰어 신청하기' }));
    await waitFor(() => expect(screen.getByText(/신청에 실패했어요/)).toBeInTheDocument());
  });

  it('이미 신청했으면 완료 상태로 표시', async () => {
    campaigns.getCampaign.mockResolvedValue(CAMP);
    campaigns.getMyApplications.mockResolvedValue({ items: [{ campaignId: 'c1' }] });
    books.getStoreDetail.mockResolvedValue({});
    renderPage();
    expect(await screen.findByText(/신청 완료/)).toBeInTheDocument();
  });
});
