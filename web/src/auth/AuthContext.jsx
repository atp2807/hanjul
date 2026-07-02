// 인증 컨텍스트 — @hanjul/lib 공용 팩토리로 생성 (loadUser·필드명만 앱 고유).
import { createAuthContext } from '@hanjul/lib';

import { getToken, setToken } from '../services/api/api_client';
import { getMe } from '../services/api/auth';

const { AuthProvider, useAuthContext } = createAuthContext({
  getToken,
  setToken,
  loadUser: getMe,
  userKey: 'user',
});

export { AuthProvider };
export const useAuth = useAuthContext;
