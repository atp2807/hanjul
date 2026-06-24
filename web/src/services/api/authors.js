import { apiClient } from './api_client';

// 작가 공개 프로필 (이름·소개·출판작)
export function getAuthor(id) {
  return apiClient.get(`/authors/${id}`);
}
// 내 작가 소개(bio) 수정
export function updateProfile(bio) {
  return apiClient.put('/me/profile', { bio });
}
