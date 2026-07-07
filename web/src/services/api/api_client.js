// API 클라이언트 — @hanjul/lib 공용 팩토리로 생성 (토큰키만 앱 고유).
import { createApiClient } from '@hanjul/lib';

const client = createApiClient('hanjul_token');

export const apiClient = client;
export const getToken = client.getToken;
export const setToken = client.setToken;

// API 오리진 베이스 — dev는 '' (vite proxy가 /api 처리), prod는 VITE_API_BASE_URL.
// 다운로드/미디어 절대경로(수출 <a href>, 이미지 표시 매핑)를 만들 때 쓴다.
export const apiBase = import.meta.env.VITE_API_BASE_URL || '';
