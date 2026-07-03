import { apiClient } from './api_client';

// 등급 기준 원문(8기준×4단계 가이드) — 인증 불필요
export function getCriteria() {
  return apiClient.get('/content-rating/criteria');
}

// 본문 기반 AI 자동분류 추천 (소유 작가만) → { contentRating, contentRatingDetail }
export function suggestRating(bookId) {
  return apiClient.post(`/books/${bookId}/content-rating/suggest`);
}

// 작가 오버라이드 저장 — detail = { 카테고리: tier } (일부/전체)
export function setRating(bookId, detail) {
  return apiClient.put(`/books/${bookId}/content-rating`, { detail });
}
