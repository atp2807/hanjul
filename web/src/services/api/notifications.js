import { apiClient } from './api_client';

// 인앱 알림함 — 목록 + 안읽음 수
export function getNotifications() {
  return apiClient.get('/me/notifications');
}
// 알림 하나 읽음 처리
export function markRead(id) {
  return apiClient.post(`/me/notifications/${id}/read`);
}
// 전체 읽음
export function markAllRead() {
  return apiClient.post('/me/notifications/read-all');
}

// 작가 팔로우 상태/구독/해제 (신간 출판 시 알림)
export function getFollowStatus(authorId) {
  return apiClient.get(`/authors/${authorId}/follow`);
}
export function followAuthor(authorId) {
  return apiClient.post(`/authors/${authorId}/follow`);
}
export function unfollowAuthor(authorId) {
  return apiClient.del(`/authors/${authorId}/follow`);
}
