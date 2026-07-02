// API 클라이언트 — @hanjul/lib 공용 팩토리로 생성 (토큰키만 앱 고유).
import { createApiClient } from '@hanjul/lib';

const client = createApiClient('hanjul_token');

export const apiClient = client;
export const getToken = client.getToken;
export const setToken = client.setToken;
