import { apiClient } from './api_client';

// 현재 로그인 계정
export function getMe() {
  return apiClient.get('/me');
}

// 소셜 로그인 시작 URL (백엔드가 Google authorize URL 생성)
export function getLoginUrl(provider = 'google') {
  return apiClient.get(`/auth/${provider}/login`);
}

// 개인정보 열람/다운로드 (개인정보보호법 §35)
export function exportMyData() {
  return apiClient.get('/me/export');
}

// 회원탈퇴 (익명화 + 소셜 연결 삭제)
export function withdraw() {
  return apiClient.del('/me');
}
