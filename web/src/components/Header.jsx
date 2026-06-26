import { Link, NavLink, useNavigate } from 'react-router-dom';

import { useAuth } from '../auth/AuthContext';
import { T } from '../theme';
import { NotificationBell } from './NotificationBell';

const NAV = [
  ['/', '서점'],
  ['/studio', '에디터'],
  ['/studio', '출판'],
  ['/pricing', '요금제'],
];

function navStyle({ isActive }) {
  return {
    padding: '9px 16px',
    borderRadius: T.radius.md,
    fontSize: 15,
    fontWeight: 600,
    color: T.text,
    textDecoration: 'none',
    background: isActive ? T.tint : 'transparent',
  };
}

export function Header() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const goLogin = () => navigate('/login');

  return (
    <header
      style={{
        position: 'sticky',
        top: 0,
        zIndex: 50,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '16px 32px',
        background: 'rgba(243,250,248,0.86)',
        backdropFilter: 'blur(12px)',
        WebkitBackdropFilter: 'blur(12px)',
        borderBottom: `1px solid ${T.border}`,
      }}
    >
      <Link to="/" style={{ display: 'flex', alignItems: 'center', gap: 9, textDecoration: 'none' }}>
        <span style={{ width: 26, height: 26, borderRadius: 8, background: T.accent, display: 'inline-block' }} />
        <span style={{ fontSize: 22, fontWeight: 800, letterSpacing: '-0.03em', color: T.ink }}>한줄</span>
      </Link>

      <nav style={{ display: 'flex', gap: 6 }}>
        {NAV.map(([to, label], i) => (
          <NavLink key={`${to}-${i}`} to={to} end={to === '/'} style={navStyle}>
            {label}
          </NavLink>
        ))}
      </nav>

      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        {user ? (
          <>
            <Link to="/library" style={{ fontSize: 14, color: T.textMid, textDecoration: 'none', fontWeight: 600 }}>
              내 서재
            </Link>
            <NotificationBell />
            <span style={{ fontSize: 14, color: T.textMid }}>{user.displayName || user.email}</span>
            <button
              onClick={logout}
              style={{ padding: '7px 14px', borderRadius: T.radius.pill, border: `1px solid ${T.border}`, background: T.surface, color: T.textMid, fontWeight: 600, cursor: 'pointer' }}
            >
              로그아웃
            </button>
          </>
        ) : (
          <>
            <span onClick={goLogin} style={{ fontSize: 14, color: T.textMid, fontWeight: 600, cursor: 'pointer' }}>
              로그인
            </span>
            <button
              onClick={goLogin}
              style={{ padding: '10px 20px', background: T.ink, color: T.inkText, border: 'none', borderRadius: T.radius.pill, fontSize: 14, fontWeight: 600, cursor: 'pointer' }}
            >
              무료로 시작
            </button>
          </>
        )}
      </div>
    </header>
  );
}
