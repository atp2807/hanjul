import { Link } from 'react-router-dom';

import { useAuth } from '../auth/AuthContext';
import { getLoginUrl } from '../services/api/auth';
import { NotificationBell } from './NotificationBell';

export function Header() {
  const { user, logout } = useAuth();

  async function startLogin() {
    const { authorizationUrl } = await getLoginUrl('google');
    window.location.href = authorizationUrl; // Google 동의 화면으로 이동
  }

  return (
    <header
      style={{
        borderBottom: '1px solid #eee',
        padding: '14px 24px',
        display: 'flex',
        alignItems: 'center',
        gap: 16,
        position: 'sticky',
        top: 0,
        background: '#fff',
        zIndex: 10,
      }}
    >
      <Link to="/" style={{ textDecoration: 'none', color: '#111' }}>
        <strong style={{ fontSize: 22, letterSpacing: '-0.02em' }}>한줄</strong>
      </Link>
      <span style={{ color: '#999', fontSize: 13 }}>글로벌 ebook 출판</span>

      <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 12 }}>
        {user ? (
          <>
            <Link to="/studio" style={{ fontSize: 14, color: '#333', textDecoration: 'none' }}>
              스튜디오
            </Link>
            <Link to="/library" style={{ fontSize: 14, color: '#333', textDecoration: 'none' }}>
              내 서재
            </Link>
            <NotificationBell />
            <span style={{ fontSize: 14, color: '#555' }}>{user.displayName || user.email}</span>
            <button onClick={logout} style={{ padding: '6px 12px', borderRadius: 8, border: '1px solid #ddd' }}>
              로그아웃
            </button>
          </>
        ) : (
          <button
            onClick={startLogin}
            style={{ padding: '8px 16px', borderRadius: 8, border: '1px solid #ddd', fontWeight: 600 }}
          >
            Google 로그인
          </button>
        )}
      </div>
    </header>
  );
}
