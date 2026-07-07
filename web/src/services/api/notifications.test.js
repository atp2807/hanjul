import { describe, expect, it, vi } from 'vitest';

import { mockApiClient } from '@hanjul/test-utils';
import { apiClient } from './api_client';
import { followAuthor, getFollowStatus, getNotifications, markAllRead, markRead, unfollowAuthor } from './notifications';

vi.mock('./api_client', () => ({
  apiClient: mockApiClient(),
}));

describe('services/api/notifications', () => {
  it('getNotifications → GET /me/notifications', () => {
    getNotifications();
    expect(apiClient.get).toHaveBeenCalledWith('/me/notifications');
  });

  it('markRead → POST /me/notifications/:id/read', () => {
    markRead('n1');
    expect(apiClient.post).toHaveBeenCalledWith('/me/notifications/n1/read');
  });

  it('markAllRead → POST /me/notifications/read-all', () => {
    markAllRead();
    expect(apiClient.post).toHaveBeenCalledWith('/me/notifications/read-all');
  });

  it('getFollowStatus → GET /authors/:id/follow', () => {
    getFollowStatus('a1');
    expect(apiClient.get).toHaveBeenCalledWith('/authors/a1/follow');
  });

  it('followAuthor → POST /authors/:id/follow', () => {
    followAuthor('a1');
    expect(apiClient.post).toHaveBeenCalledWith('/authors/a1/follow');
  });

  it('unfollowAuthor → DELETE /authors/:id/follow', () => {
    unfollowAuthor('a1');
    expect(apiClient.del).toHaveBeenCalledWith('/authors/a1/follow');
  });
});
