import { fireEvent, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { renderWithProviders, authFixture } from '@hanjul/test-utils';
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
vi.mock('../auth/AuthContext', () => ({ useAuth: () => authFixture({ user: { id: 'u1' } }) }));

function renderPage() {
  return renderWithProviders(<CampaignStudioPage />);
}

describe('CampaignStudioPage', () => {
  beforeEach(() => { vi.clearAllMocks(); });

  it('집계 + 캠페인 행 + 신청자 배정', async () => {
    campaigns.getMyCampaigns.mockResolvedValue({ items: [
      { id: 'c1', bookId: 'b1', bookTitle: '관리책', slots: 10, filled: 3, remaining: 7, status: 'OPEN', applicants: 5, reviewed: 2 },
    ] });
    studio.getMyBooks.mockResolvedValue({ items: [{ id: 'b1', title: '관리책', status: 'PUBLISHED' }] });
    campaigns.getApplicants.mockResolvedValue({ items: [
      { id: 'ap1', applicantId: 'u9', applicantName: '리뷰어A', status: 'PENDING', deadlineAt: null },
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
      { id: 'c1', bookId: 'b1', bookTitle: '마감대상', slots: 10, filled: 1, remaining: 9, status: 'OPEN', applicants: 3, reviewed: 0 },
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

  it('목록 로드 실패 → 빈 목록으로 둔갑하지 않고 에러 표시', async () => {
    campaigns.getMyCampaigns.mockRejectedValue(new Error('API 500'));
    studio.getMyBooks.mockResolvedValue({ items: [] });
    renderPage();
    expect(await screen.findByText('캠페인 목록을 불러오지 못했어요.')).toBeInTheDocument();
    expect(screen.queryByText('아직 캠페인이 없어요')).not.toBeInTheDocument();
  });

  it('마감 실패 → 에러 안내 (침묵 금지)', async () => {
    campaigns.getMyCampaigns.mockResolvedValue({ items: [
      { id: 'c1', bookId: 'b1', bookTitle: '마감대상', slots: 10, filled: 1, remaining: 9, status: 'OPEN', applicants: 3, reviewed: 0 },
    ] });
    studio.getMyBooks.mockResolvedValue({ items: [] });
    campaigns.closeCampaign.mockRejectedValue(new Error('API 500'));
    renderPage();
    fireEvent.click(await screen.findByRole('button', { name: '마감' }));
    expect(await screen.findByText(/캠페인 마감에 실패했어요/)).toBeInTheDocument();
  });

  it('배정 실패 → 에러 안내 (침묵 금지)', async () => {
    campaigns.getMyCampaigns.mockResolvedValue({ items: [
      { id: 'c1', bookId: 'b1', bookTitle: '관리책', slots: 10, filled: 3, remaining: 7, status: 'OPEN', applicants: 5, reviewed: 2 },
    ] });
    studio.getMyBooks.mockResolvedValue({ items: [] });
    campaigns.getApplicants.mockResolvedValue({ items: [
      { id: 'ap1', applicantId: 'u9', applicantName: '리뷰어A', status: 'PENDING' },
    ] });
    campaigns.assignReviewer.mockRejectedValue(new Error('API 500'));
    renderPage();

    fireEvent.click(await screen.findByRole('button', { name: '신청자' }));
    fireEvent.click(await screen.findByRole('button', { name: '배정' }));
    expect(await screen.findByText(/배정에 실패했어요/)).toBeInTheDocument();
  });

  it('신청자 목록 로드 실패 → 에러 + 다시 시도', async () => {
    campaigns.getMyCampaigns.mockResolvedValue({ items: [
      { id: 'c1', bookId: 'b1', bookTitle: '관리책', slots: 10, filled: 3, remaining: 7, status: 'OPEN', applicants: 5, reviewed: 2 },
    ] });
    studio.getMyBooks.mockResolvedValue({ items: [] });
    campaigns.getApplicants
      .mockRejectedValueOnce(new Error('API 500'))
      .mockResolvedValueOnce({ items: [{ id: 'ap1', applicantId: 'u9', applicantName: '리뷰어A', status: 'PENDING' }] });
    renderPage();

    fireEvent.click(await screen.findByRole('button', { name: '신청자' }));
    expect(await screen.findByText('신청자 목록을 불러오지 못했어요.')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '다시 시도' }));
    expect(await screen.findByText('리뷰어A')).toBeInTheDocument();
  });

  it('새 캠페인 게시 — 성공 시 목록 갱신 + 패널 닫힘', async () => {
    campaigns.getMyCampaigns.mockResolvedValue({ items: [] });
    studio.getMyBooks.mockResolvedValue({ items: [{ id: 'b1', title: '관리책', status: 'PUBLISHED' }] });
    campaigns.createCampaign.mockResolvedValue({ id: 'c1' });
    renderPage();

    await screen.findByText(/아직 캠페인이 없어요/);
    fireEvent.click(screen.getByRole('button', { name: '＋ 새 캠페인' }));
    expect(await screen.findByText('새 서평단 캠페인')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '캠페인 게시' }));

    await waitFor(() => expect(campaigns.createCampaign).toHaveBeenCalledWith({ bookId: 'b1', slots: 10, reviewDays: 14, minChars: 300 }));
    await waitFor(() => expect(campaigns.getMyCampaigns).toHaveBeenCalledTimes(2)); // 최초 로드 + 게시 후 재로드
    expect(screen.queryByText('새 서평단 캠페인')).not.toBeInTheDocument();
  });

  it('새 캠페인 게시 실패 → 에러 안내, 패널 유지', async () => {
    campaigns.getMyCampaigns.mockResolvedValue({ items: [] });
    studio.getMyBooks.mockResolvedValue({ items: [{ id: 'b1', title: '관리책', status: 'PUBLISHED' }] });
    campaigns.createCampaign.mockRejectedValue(new Error('API 500'));
    renderPage();

    await screen.findByText(/아직 캠페인이 없어요/);
    fireEvent.click(screen.getByRole('button', { name: '＋ 새 캠페인' }));
    fireEvent.click(await screen.findByRole('button', { name: '캠페인 게시' }));
    expect(await screen.findByText(/캠페인 게시에 실패했어요/)).toBeInTheDocument();
    expect(screen.getByText('새 서평단 캠페인')).toBeInTheDocument(); // 패널은 그대로
  });

  it('출판한 책이 없으면 캠페인 생성 대신 안내', async () => {
    campaigns.getMyCampaigns.mockResolvedValue({ items: [] });
    studio.getMyBooks.mockResolvedValue({ items: [] });
    renderPage();

    await screen.findByText(/아직 캠페인이 없어요/);
    fireEvent.click(screen.getByRole('button', { name: '＋ 새 캠페인' }));
    expect(await screen.findByText('먼저 책을 출판해야 캠페인을 열 수 있어요.')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '캠페인 게시' })).not.toBeInTheDocument();
  });

  it('취소 버튼 → 패널 닫힘', async () => {
    campaigns.getMyCampaigns.mockResolvedValue({ items: [] });
    studio.getMyBooks.mockResolvedValue({ items: [{ id: 'b1', title: '관리책', status: 'PUBLISHED' }] });
    renderPage();

    await screen.findByText(/아직 캠페인이 없어요/);
    fireEvent.click(screen.getByRole('button', { name: '＋ 새 캠페인' }));
    fireEvent.click(await screen.findByRole('button', { name: '취소' }));
    expect(screen.queryByText('새 서평단 캠페인')).not.toBeInTheDocument();
  });

  it('출판한 책 목록 로드 실패 시 생성 패널에서도 에러 안내', async () => {
    campaigns.getMyCampaigns.mockResolvedValue({ items: [] });
    studio.getMyBooks.mockRejectedValue(new Error('API 500'));
    renderPage();

    await screen.findByText(/아직 캠페인이 없어요/);
    fireEvent.click(screen.getByRole('button', { name: '＋ 새 캠페인' }));
    expect(await screen.findByText(/출판한 책 목록을 불러오지 못했어요/)).toBeInTheDocument();
  });
});
