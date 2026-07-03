import { describe, expect, it, vi } from 'vitest';

import { apiClient } from './api_client';
import { getCriteria, setRating, suggestRating } from './contentRating';

vi.mock('./api_client', () => ({
  apiClient: { get: vi.fn(), post: vi.fn(), put: vi.fn() },
}));

describe('services/api/contentRating', () => {
  it('getCriteria → GET /content-rating/criteria', () => {
    getCriteria();
    expect(apiClient.get).toHaveBeenCalledWith('/content-rating/criteria');
  });

  it('suggestRating → POST /books/:id/content-rating/suggest', () => {
    suggestRating('b1');
    expect(apiClient.post).toHaveBeenCalledWith('/books/b1/content-rating/suggest');
  });

  it('setRating → PUT /books/:id/content-rating with { detail }', () => {
    const detail = { theme: 'ALL', violence: 'AGE15' };
    setRating('b1', detail);
    expect(apiClient.put).toHaveBeenCalledWith('/books/b1/content-rating', { detail });
  });
});
