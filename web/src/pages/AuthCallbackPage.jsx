import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

import { useAuth } from '../auth/AuthContext';

// 백엔드가 /auth/callback#token=...&isNew=... 로 리다이렉트 → fragment에서 토큰 저장.
export function AuthCallbackPage() {
  const { login } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    const params = new URLSearchParams(window.location.hash.replace(/^#/, ''));
    const token = params.get('token');
    if (token) login(token);
    navigate('/', { replace: true });
  }, [login, navigate]);

  return <p style={{ padding: 40, color: '#999', textAlign: 'center' }}>로그인 처리 중…</p>;
}
