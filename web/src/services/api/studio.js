import { apiClient } from './api_client';

// 작가 — 내 책 목록 (전 상태)
export function getMyBooks() {
  return apiClient.get('/me/books');
}
export function getSales() {
  return apiClient.get('/me/sales');
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
// 기간 할인 — until: ISO 시각
export function setDiscount(bookId, amount, until) {
  return apiClient.put(`/books/${bookId}/discount`, { amount, until });
}
export function submitBook(bookId) {
  return apiClient.post(`/books/${bookId}/submit`);
}
export function publishBook(bookId) {
  return apiClient.post(`/books/${bookId}/publish`);
}
// 즉시 출간 (심사 생략)
export function publishNow(bookId) {
  return apiClient.post(`/books/${bookId}/publish-now`);
}
// 출판 취소 (비공개로 내림)
export function unpublishBook(bookId) {
  return apiClient.post(`/books/${bookId}/unpublish`);
}
// 무료 미리보기 공개 분량(블록 수)
export function setPreviewLimit(bookId, limit) {
  return apiClient.put(`/books/${bookId}/preview-limit`, { limit });
}
// 예약 발행 — ISO 시각 (백그라운드 스케줄러가 게시)
export function schedulePublish(bookId, publishAt) {
  return apiClient.post(`/books/${bookId}/schedule`, { publishAt });
}
export function setIsbn(bookId, isbn) {
  return apiClient.put(`/books/${bookId}/isbn`, { isbn });
}
// 부제·소개·분류 일괄 저장
export function updateMeta(bookId, { subtitle, description, category }) {
  return apiClient.put(`/books/${bookId}/meta`, { subtitle, description, category });
}
// AI 표지 생성 (프롬프트 → 이미지 URL, 책에 연결)
export function generateCover(bookId, prompt) {
  return apiClient.post(`/books/${bookId}/cover`, { prompt });
}
// 에디터 정본 전체 교체 (원클릭 출판) — chapters=[{title, blocks:[{type,html}]}]
export function setBookContent(bookId, chapters) {
  return apiClient.put(`/books/${bookId}/content`, { chapters });
}
// 서점 배포 — channel: KYOBO | YES24 | ALADIN ...
export function distributeBook(bookId, channel) {
  return apiClient.post(`/books/${bookId}/distribute`, { channel });
}
export function getDistributions(bookId) {
  return apiClient.get(`/books/${bookId}/distributions`);
}
export function downloadEpub(bookId) {
  return apiClient.download(`/books/${bookId}/epub`, `${bookId}.epub`);
}
export function downloadOnix(bookId) {
  return apiClient.download(`/books/${bookId}/onix`, `${bookId}.onix.xml`);
}
