import { describe, expect, it, vi } from 'vitest';

import { apiClient } from './api_client';
import { getAuthor, updateProfile } from './authors';

vi.mock('./api_client', () => ({
  apiClient: { get: vi.fn(), post: vi.fn(), put: vi.fn(), del: vi.fn() },
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
