import { fireEvent, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { renderWithProviders, authFixture } from '@hanjul/test-utils';
import * as campaigns from '../services/api/campaigns';
import * as reviews from '../services/api/reviews';
import { ReviewCopyReviewPage } from './ReviewCopyReviewPage';

vi.mock('../services/api/campaigns', async (orig) => ({ ...(await orig()), getCampaign: vi.fn(), getMyApplications: vi.fn() }));
vi.mock('../services/api/reviews');
vi.mock('../auth/AuthContext', () => ({ useAuth: () => authFixture({ user: { id: 'u1' } }) }));

function renderPage() {
  return renderWithProviders(<ReviewCopyReviewPage />, { path: '/campaigns/:id/review', at: '/campaigns/c1/review' });
}

describe('ReviewCopyReviewPage', () => {
  it('별점·최소분량 충족 전엔 제출이 막히고, 충족 후 제출된다', async () => {
    campaigns.getCampaign.mockResolvedValue({ bookId: 'b1', bookTitle: '밤의 편집자', minChars: 10 });
    campaigns.getMyApplications.mockResolvedValue({ items: [{ campaignId: 'c1', deadlineAt: '2099-01-01T00:00:00Z' }] });
    reviews.addReview.mockResolvedValue({ ok: true });
    renderPage();

    const submit = await screen.findByText('리뷰 제출');
    expect(submit).toBeDisabled(); // 별점·내용 없음

    fireEvent.click(screen.getByRole('button', { name: '별점 5점' })); // 별 5점
    fireEvent.change(screen.getByPlaceholderText(/솔직하게 평가/), { target: { value: '짧음' } });
    expect(submit).toBeDisabled(); // 최소 10자 미달

    fireEvent.change(screen.getByPlaceholderText(/솔직하게 평가/), { target: { value: '충분히 긴 리뷰 내용입니다' } });
    expect(submit).not.toBeDisabled();

    fireEvent.click(submit);
    await waitFor(() => expect(reviews.addReview).toHaveBeenCalledWith('b1', 5, '충분히 긴 리뷰 내용입니다'));
  });
});
