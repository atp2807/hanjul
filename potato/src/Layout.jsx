import { useEffect, useState } from 'react';
import { NavLink, Outlet } from 'react-router-dom';

import { api } from './api';
import { useOps } from './auth.jsx';
import { T } from './theme';
import { Icon } from './ui.jsx';

const NAV = [
  { to: '/', label: '대시보드', icon: 'dashboard', end: true },
  { to: '/moderation', label: '모더레이션', icon: 'moderation', badge: 'booksBlocked', tone: T.danger },
  { to: '/reports', label: '신고', icon: 'reports', badge: 'reportsOpen', tone: T.danger },
  { to: '/accounts', label: '계정', icon: 'accounts' },
];

export default function Layout() {
  const { operator, logout } = useOps();
  const [stats, setStats] = useState(null);

  useEffect(() => {
    api.dashboard().then(setStats).catch(() => {});
  }, []);

  return (
    <div style={{ display: 'flex', minHeight: '100vh', background: T.bg }}>
      <aside
        style={{
          width: 236,
          background: T.sidebar,
          padding: '24px 16px',
          display: 'flex',
          flexDirection: 'column',
          flexShrink: 0,
        }}
      >
        {/* 로고 + 운영 배지 */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 9, marginBottom: 28, padding: '0 6px' }}>
          <span style={{ width: 24, height: 24, borderRadius: 7, background: T.accent }} />
          <span style={{ fontSize: 16, fontWeight: 800, color: T.inkText }}>한줄</span>
          <span
            style={{
              padding: '2px 7px',
              background: 'rgba(255,255,255,0.12)',
              color: '#8fcfc4',
              borderRadius: 6,
              fontSize: 10,
              fontWeight: 800,
              letterSpacing: '0.06em',
            }}
          >
            운영
          </span>
        </div>

        {/* nav */}
        <nav style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
          {NAV.map((it) => {
            const count = it.badge && stats ? stats[it.badge] : 0;
            return (
              <NavLink
                key={it.to}
                to={it.to}
                end={it.end}
                style={({ isActive }) => ({
                  display: 'flex',
                  alignItems: 'center',
                  gap: 11,
                  padding: '11px 13px',
                  borderRadius: 10,
                  fontSize: 14,
                  fontWeight: isActive ? 700 : 500,
                  color: isActive ? '#fff' : T.sidebarText,
                  background: isActive ? 'rgba(255,255,255,0.12)' : 'transparent',
                  textDecoration: 'none',
                })}
              >
                <Icon name={it.icon} size={18} />
                <span style={{ flex: 1 }}>{it.label}</span>
                {count > 0 && (
                  <span
                    style={{
                      padding: '1px 8px',
                      background: it.tone || T.accent,
                      color: '#fff',
                      borderRadius: 999,
                      fontSize: 11,
                      fontWeight: 800,
                    }}
                  >
                    {count}
                  </span>
                )}
              </NavLink>
            );
          })}
        </nav>

        {/* 하단 유저 카드 */}
        <div style={{ marginTop: 'auto' }}>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 10,
              padding: 10,
              borderRadius: 12,
              background: 'rgba(255,255,255,0.06)',
              marginBottom: 10,
            }}
          >
            <span
              style={{
                width: 34,
                height: 34,
                borderRadius: 999,
                background: 'linear-gradient(140deg,#1d7e8e,#2aa0a8)',
                flexShrink: 0,
              }}
            />
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontSize: 13, fontWeight: 700, color: T.inkText, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {operator?.name}
              </div>
              <div style={{ fontSize: 11, color: T.sidebarMuted }}>
                {operator?.roleCd === 'DEVELOPER' ? '개발자' : '운영자'}
              </div>
            </div>
          </div>
          <button
            onClick={logout}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              width: '100%',
              font: T.font,
              fontSize: 13,
              fontWeight: 600,
              color: T.sidebarText,
              background: 'transparent',
              border: '1px solid rgba(255,255,255,0.16)',
              borderRadius: 10,
              padding: '9px 12px',
              cursor: 'pointer',
            }}
          >
            <Icon name="logout" size={16} />
            로그아웃
          </button>
        </div>
      </aside>

      <main style={{ flex: 1, padding: '30px 36px', maxWidth: 1140, overflow: 'hidden' }}>
        <Outlet />
      </main>
    </div>
  );
}
