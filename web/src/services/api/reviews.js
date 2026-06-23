import { apiClient } from './api_client';

// 책 평점·리뷰 목록 (평균/개수/항목)
export function getReviews(bookId) {
  return apiClient.get(`/books/${bookId}/reviews`);
}
// 리뷰 작성(로그인 필요) — rating 1~5, (책,계정)당 한 건(재작성=갱신)
export function addReview(bookId, rating, body) {
  return apiClient.post(`/books/${bookId}/reviews`, { rating, body });
}
