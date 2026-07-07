import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { mockApiClient } from '@hanjul/test-utils';
import { apiClient } from './api_client';
import {
  applyCampaign,
  assignReviewer,
  cancelApplication,
  closeCampaign,
  createCampaign,
  dday,
  getApplicants,
  getCampaign,
  getMyApplications,
  getMyCampaigns,
  getReviewerStatus,
  listOpenCampaigns,
} from './campaigns';

vi.mock('./api_client', () => ({
  apiClient: mockApiClient(),
}));

describe('services/api/campaigns', () => {
  it('listOpenCampaigns → category 없으면 그대로', () => {
    listOpenCampaigns();
    expect(apiClient.get).toHaveBeenCalledWith('/campaigns/open');
  });

  it('listOpenCampaigns → category 인코딩', () => {
    listOpenCampaigns('경제·경영');
    expect(apiClient.get).toHaveBeenCalledWith(`/campaigns/open?category=${encodeURIComponent('경제·경영')}`);
  });

  it('getCampaign → GET /campaigns/:id', () => {
    getCampaign('c1');
    expect(apiClient.get).toHaveBeenCalledWith('/campaigns/c1');
  });

  it('applyCampaign → POST /campaigns/:id/apply', () => {
    applyCampaign('c1');
    expect(apiClient.post).toHaveBeenCalledWith('/campaigns/c1/apply');
  });

  it('cancelApplication → DELETE /campaigns/:id/apply', () => {
    cancelApplication('c1');
    expect(apiClient.del).toHaveBeenCalledWith('/campaigns/c1/apply');
  });

  it('getMyApplications → GET /me/applications', () => {
    getMyApplications();
    expect(apiClient.get).toHaveBeenCalledWith('/me/applications');
  });

  it('getReviewerStatus → GET /me/reviewer-status', () => {
    getReviewerStatus();
    expect(apiClient.get).toHaveBeenCalledWith('/me/reviewer-status');
  });

  it('createCampaign → reviewDays·minChars 기본값 채움', () => {
    createCampaign({ bookId: 'b1', slots: 10 });
    expect(apiClient.post).toHaveBeenCalledWith('/campaigns', { bookId: 'b1', slots: 10, reviewDays: 14, minChars: 0 });
  });

  it('createCampaign → 값 지정 시 그대로', () => {
    createCampaign({ bookId: 'b1', slots: 5, reviewDays: 7, minChars: 300 });
    expect(apiClient.post).toHaveBeenCalledWith('/campaigns', { bookId: 'b1', slots: 5, reviewDays: 7, minChars: 300 });
  });

  it('getMyCampaigns → GET /me/campaigns', () => {
    getMyCampaigns();
    expect(apiClient.get).toHaveBeenCalledWith('/me/campaigns');
  });

  it('getApplicants → GET /campaigns/:id/applications', () => {
    getApplicants('c1');
    expect(apiClient.get).toHaveBeenCalledWith('/campaigns/c1/applications');
  });

  it('assignReviewer → POST /campaigns/:id/assign', () => {
    assignReviewer('c1', 'u9');
    expect(apiClient.post).toHaveBeenCalledWith('/campaigns/c1/assign', { applicantId: 'u9' });
  });

  it('closeCampaign → POST /campaigns/:id/close', () => {
    closeCampaign('c1');
    expect(apiClient.post).toHaveBeenCalledWith('/campaigns/c1/close');
  });
});

describe('dday', () => {
  const NOW = new Date('2026-07-03T00:00:00Z').getTime();
  beforeEach(() => { vi.useFakeTimers(); vi.setSystemTime(NOW); });
  afterEach(() => { vi.useRealTimers(); });

  it('deadlineAt 없으면 null', () => {
    expect(dday(null)).toBeNull();
    expect(dday(undefined)).toBeNull();
  });

  it('지난 기한 → 마감', () => {
    expect(dday('2026-07-01T00:00:00Z')).toBe('마감');
  });

  it('마감 시각이 지금 이 순간이면 D-day', () => {
    expect(dday('2026-07-03T00:00:00Z')).toBe('D-day');
  });

  it('정확히 이틀 뒤 → D-2', () => {
    expect(dday('2026-07-05T00:00:00Z')).toBe('D-2');
  });
});
