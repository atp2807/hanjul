import { apiClient } from './api_client';

// 작가 — 내 책 목록 (전 상태)
export function getMyBooks() {
  return apiClient.get('/me/books');
}
export function createBook(title, kind = 'BOOK') {
  return apiClient.post('/books', { title, kind });
}
export function importText(bookId, rawText, chapterTitle) {
  return apiClient.post(`/books/${bookId}/import`, { rawText, chapterTitle });
}
export function setBookPrice(bookId, amount) {
  return apiClient.put(`/books/${bookId}/price`, { amount });
}
export function submitBook(bookId) {
  return apiClient.post(`/books/${bookId}/submit`);
}
export function publishBook(bookId) {
  return apiClient.post(`/books/${bookId}/publish`);
}
