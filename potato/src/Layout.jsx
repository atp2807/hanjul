import { NavLink, Outlet } from 'react-router-dom';

import { useOps } from './auth.jsx';
import { T } from './theme';

const NAV = [
  { to: '/', label: '대시보드', end: true },
  { to: '/moderation', label: '모더레이션' },
  { to: '/reports', label: '신고' },
  { to: '/accounts', label: '계정' },
];

// 개발자(DEVELOPER) 전용 메뉴 — 일반 운영자에겐 숨김 (해드림 devOnly 패턴).
// Phase1엔 dev 전용 화면 없음. 시스템/엔진 메뉴 생기면 여기 추가 + dev:true.
const DEV_NAV = [];

export default function Layout() {
  const { operator, logout } = useOps();
  const isDev = operator?.roleCd === 'DEVELOPER';
  const items = [...NAV, ...(isDev ? DEV_NAV : [])];

  return (
    <div style={{ display: 'flex', minHeight: '100vh', background: T.bg }}>
      <aside
        style={{
          width: 220,
          background: T.ink,
          color: T.inkText,
          padding: '24px 16px',
          display: 'flex',
          flexDirection: 'column',
          gap: 4,
        }}
      >
        <div style={{ fontSize: 20, fontWeight: 700, padding: '0 8px 8px', letterSpacing: 0.5 }}>
          potato
          <span style={{ color: T.inkSoft, fontSize: 12, fontWeight: 500, marginLeft: 8 }}>
            한줄 운영
          </span>
        </div>
        {items.map((it) => (
          <NavLink
            key={it.to}
            to={it.to}
            end={it.end}
            style={({ isActive }) => ({
              padding: '10px 12px',
              borderRadius: T.radius.md,
              color: isActive ? T.ink : T.inkText,
              background: isActive ? T.inkText : 'transparent',
              fontWeight: 600,
              fontSize: 14,
              textDecoration: 'none',
            })}
          >
            {it.label}
            {it.dev && (
              <span style={{ fontSize: 11, color: T.inkSoft, marginLeft: 6 }}>dev</span>
            )}
          </NavLink>
        ))}
        <div style={{ marginTop: 'auto', paddingTop: 16, borderTop: `1px solid rgba(255,255,255,0.12)` }}>
          <div style={{ fontSize: 13, color: T.inkSoft }}>{operator?.name}</div>
          <div style={{ fontSize: 11, color: T.inkSoft, marginBottom: 10 }}>{operator?.roleCd}</div>
          <button
            onClick={logout}
            style={{
              font: T.font,
              fontSize: 13,
              fontWeight: 600,
              color: T.inkText,
              background: 'transparent',
              border: `1px solid rgba(255,255,255,0.25)`,
              borderRadius: T.radius.md,
              padding: '6px 12px',
              cursor: 'pointer',
            }}
          >
            로그아웃
          </button>
        </div>
      </aside>
      <main style={{ flex: 1, padding: '32px 36px', maxWidth: 1000 }}>
        <Outlet />
      </main>
    </div>
  );
}
