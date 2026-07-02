// 운영자 인증 컨텍스트 — @hanjul/lib 공용 팩토리로 생성 (필드명 operator).
import { createAuthContext } from '@hanjul/lib';

import { api, getToken, setToken } from './api';

const { AuthProvider, useAuthContext } = createAuthContext({
  getToken,
  setToken,
  loadUser: api.me,
  userKey: 'operator',
});

export const OpsAuthProvider = AuthProvider;
export const useOps = useAuthContext;
