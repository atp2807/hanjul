import { apiClient } from './api_client';

// 현재 로그인 계정
export function getMe() {
  return apiClient.get('/me');
}

// 소셜 로그인 시작 URL (백엔드가 Google authorize URL 생성)
export function getLoginUrl(provider = 'google') {
  return apiClient.get(`/auth/${provider}/login`);
}
