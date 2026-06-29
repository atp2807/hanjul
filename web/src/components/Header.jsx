import { Link, NavLink, useNavigate } from 'react-router-dom';

import { useAuth } from '../auth/AuthContext';
import { useIsMobile } from '../hooks/useIsMobile';
import { T } from '../theme';
import { BrandMark } from './BrandMark';
import { NotificationBell } from './NotificationBell';

const NAV = [
  ['/', '서점'],
  ['/studio', '에디터'],
  ['/studio', '출판'],
  ['/reviewers', '서평단'],
  ['/pricing', '수수료·정산'],
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
  const isMobile = useIsMobile();
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
        padding: isMobile ? '12px 18px' : '16px 32px',
        background: 'rgba(243,250,248,0.86)',
        backdropFilter: 'blur(12px)',
        WebkitBackdropFilter: 'blur(12px)',
        borderBottom: `1px solid ${T.border}`,
      }}
    >
      <Link to="/" style={{ display: 'flex', alignItems: 'center', gap: 9, textDecoration: 'none' }}>
        <BrandMark size={28} />
        <span style={{ fontSize: 22, fontWeight: 800, letterSpacing: '-0.03em', color: T.ink }}>한줄</span>
      </Link>

      {/* 데스크톱 상단 네비 — 모바일은 하단 탭바(MobileTabBar)가 대신함 */}
      {!isMobile && (
        <nav style={{ display: 'flex', gap: 6 }}>
          {NAV.map(([to, label], i) => (
            <NavLink key={`${to}-${i}`} to={to} end={to === '/'} style={navStyle}>
              {label}
            </NavLink>
          ))}
        </nav>
      )}

      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        {user ? (
          <>
            {!isMobile && (
              <Link to="/library" style={{ fontSize: 14, color: T.textMid, textDecoration: 'none', fontWeight: 600 }}>
                내 서재
              </Link>
            )}
            <NotificationBell />
            {!isMobile && <span style={{ fontSize: 14, color: T.textMid }}>{user.displayName || user.email}</span>}
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
