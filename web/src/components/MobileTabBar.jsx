import { useLocation, useNavigate } from 'react-router-dom';

import { useAuth } from '../auth/AuthContext';
import { useIsMobile } from '../hooks/useIsMobile';
import { T } from '../theme';

const TABS = [
  { icon: '🏠', label: '홈', to: '/' },
  { icon: '🎁', label: '서평단', to: '/reviewers' },
  { icon: '📖', label: '서재', to: '/library' },
  { icon: '✍️', label: '스튜디오', to: '/studio' },
  { icon: '👤', label: '마이', to: '__my__' },
];

// 모바일 전용 하단 탭바. 데스크톱/몰입화면(리더·에디터)에선 렌더 안 함.
export function MobileTabBar() {
  const isMobile = useIsMobile();
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const { user } = useAuth();

  const immersive = pathname.startsWith('/write/') || pathname.startsWith('/read/');
  if (!isMobile || immersive) return null;

  const resolve = (to) => (to === '__my__' ? (user ? '/reviewer/activity' : '/login') : to);
  const isActive = (to) => {
    const r = resolve(to);
    return r === '/' ? pathname === '/' : pathname.startsWith(r);
  };

  return (
    <nav
      style={{
        position: 'fixed', left: 0, right: 0, bottom: 0, zIndex: 60,
        background: 'rgba(255,255,255,0.95)', backdropFilter: 'blur(10px)', WebkitBackdropFilter: 'blur(10px)',
        borderTop: `1px solid ${T.border}`,
        padding: '9px 8px max(8px, env(safe-area-inset-bottom))',
        display: 'flex', justifyContent: 'space-around', alignItems: 'center',
      }}
    >
      {TABS.map((t) => {
        const on = isActive(t.to);
        return (
          <button
            key={t.label}
            onClick={() => navigate(resolve(t.to))}
            style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 3, background: 'none', border: 'none', cursor: 'pointer', padding: '2px 10px', opacity: on ? 1 : 0.55 }}
          >
            <span style={{ fontSize: 19, lineHeight: 1 }}>{t.icon}</span>
            <span style={{ fontSize: 10, fontWeight: on ? 700 : 600, color: on ? T.ink : T.muted }}>{t.label}</span>
          </button>
        );
      })}
    </nav>
  );
}
