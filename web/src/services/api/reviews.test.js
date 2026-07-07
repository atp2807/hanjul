import { describe, expect, it, vi } from 'vitest';

import { mockApiClient } from '@hanjul/test-utils';
import { apiClient } from './api_client';
import { addReview, getReviews } from './reviews';

vi.mock('./api_client', () => ({
  apiClient: mockApiClient(),
}));

describe('services/api/reviews', () => {
  it('getReviews → GET /books/:id/reviews', () => {
    getReviews('b1');
    expect(apiClient.get).toHaveBeenCalledWith('/books/b1/reviews');
  });

  it('addReview → POST /books/:id/reviews', () => {
    addReview('b1', 5, '좋아요');
    expect(apiClient.post).toHaveBeenCalledWith('/books/b1/reviews', { rating: 5, body: '좋아요' });
  });
});
