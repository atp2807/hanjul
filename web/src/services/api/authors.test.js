import { describe, expect, it, vi } from 'vitest';

import { mockApiClient } from '@hanjul/test-utils';
import { apiClient } from './api_client';
import { getAuthor, updateProfile } from './authors';

vi.mock('./api_client', () => ({
  apiClient: mockApiClient(),
}));

describe('services/api/authors', () => {
  it('getAuthor → GET /authors/:id', () => {
    getAuthor('a1');
    expect(apiClient.get).toHaveBeenCalledWith('/authors/a1');
  });

  it('updateProfile → PUT /me/profile', () => {
    updateProfile('새 소개');
    expect(apiClient.put).toHaveBeenCalledWith('/me/profile', { bio: '새 소개' });
  });
});
