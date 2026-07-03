import { describe, expect, it, vi } from 'vitest';

import { apiClient } from './api_client';
import { exportMyData, getLoginUrl, getMe, withdraw } from './auth';

vi.mock('./api_client', () => ({
  apiClient: { get: vi.fn(), post: vi.fn(), put: vi.fn(), del: vi.fn() },
}));

describe('services/api/auth', () => {
  it('getMe → GET /me', () => {
    getMe();
    expect(apiClient.get).toHaveBeenCalledWith('/me');
  });

  it('getLoginUrl → provider 기본값 google', () => {
    getLoginUrl();
    expect(apiClient.get).toHaveBeenCalledWith('/auth/google/login');
  });

  it('getLoginUrl → provider 지정', () => {
    getLoginUrl('naver');
    expect(apiClient.get).toHaveBeenCalledWith('/auth/naver/login');
  });

  it('exportMyData → GET /me/export', () => {
    exportMyData();
    expect(apiClient.get).toHaveBeenCalledWith('/me/export');
  });

  it('withdraw → DELETE /me', () => {
    withdraw();
    expect(apiClient.del).toHaveBeenCalledWith('/me');
  });
});
