import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

import * as campaigns from '../services/api/campaigns';
import { ReviewersPage } from './ReviewersPage';

vi.mock('../services/api/campaigns', async (orig) => ({
  ...(await orig()),
  listOpenCampaigns: vi.fn(),
}));
vi.mock('../auth/AuthContext', () => ({ useAuth: () => ({ user: null }) }));

function renderPage() {
  return render(
    <MemoryRouter>
      <ReviewersPage />
    </MemoryRouter>,
  );
}

describe('ReviewersPage', () => {
  it('모집중 캠페인을 카드로 렌더한다', async () => {
    campaigns.listOpenCampaigns.mockResolvedValue({
      items: [
        { id: 'c1', bookTitle: '밤의 편집자', slots: 30, filled: 23, remaining: 7, statusCd: 'OPEN' },
      ],
    });
    renderPage();
    expect(await screen.findByText('밤의 편집자')).toBeInTheDocument();
    expect(screen.getAllByText('7부').length).toBeGreaterThanOrEqual(1); // 남은 증정본
  });

  it('모집이 없으면 빈 상태 안내', async () => {
    campaigns.listOpenCampaigns.mockResolvedValue({ items: [] });
    renderPage();
    expect(await screen.findByText('모집 중인 캠페인이 없어요')).toBeInTheDocument();
  });
});
