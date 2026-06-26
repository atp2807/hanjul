import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';

import { useAuth } from '../auth/AuthContext';

const ERROR_MSG = {
  access_denied: '로그인을 취소했어요.',
  no_code: '로그인 정보가 없어요. 다시 시도해 주세요.',
  auth_failed: '구글 인증에 실패했어요. 잠시 후 다시 시도해 주세요.',
};

// 백엔드가 /auth/callback#token=...&isNew=... (성공) 또는 #error=... (실패) 로 리다이렉트.
export function AuthCallbackPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [error, setError] = useState(null);

  useEffect(() => {
    const params = new URLSearchParams(window.location.hash.replace(/^#/, ''));
    const token = params.get('token');
    const err = params.get('error');
    if (token) {
      login(token);
      navigate('/', { replace: true });
    } else if (err) {
      setError(ERROR_MSG[err] || '로그인에 실패했어요.');
    } else {
      navigate('/', { replace: true });
    }
  }, [login, navigate]);

  if (error) {
    return (
      <div style={{ padding: 40, textAlign: 'center' }}>
        <p style={{ color: '#e11d48' }}>{error}</p>
        <Link to="/" style={{ color: '#2563eb' }}>홈으로</Link>
      </div>
    );
  }
  return <p style={{ padding: 40, color: '#999', textAlign: 'center' }}>로그인 처리 중…</p>;
}
