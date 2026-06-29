import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { useAuth } from '../auth/AuthContext';
import { useIsMobile } from '../hooks/useIsMobile';
import { KIND_ICON, KIND_ICON_BG, KIND_LABEL, KIND_SUFFIX } from '../notificationKinds';
import { getNotifications, markAllRead, markRead } from '../services/api/notifications';
import { T } from '../theme';

export function NotificationsPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const isMobile = useIsMobile();
  const [items, setItems] = useState(null);
  const [filter, setFilter] = useState('ALL'); // ALL | UNREAD

  function load() {
    getNotifications().then((r) => setItems(r.items)).catch(() => setItems([]));
  }
  useEffect(() => { if (user) load(); }, [user]);

  if (!user) return <div style={{ padding: 60, textAlign: 'center', color: T.muted, fontFamily: T.font }}>로그인이 필요해요.</div>;
  if (items === null) return <div style={{ padding: 60, textAlign: 'center', color: T.muted, fontFamily: T.font }}>불러오는 중…</div>;

  const unread = items.filter((n) => !n.readYn).length;
  const shown = filter === 'UNREAD' ? items.filter((n) => !n.readYn) : items;

  async function onItem(n) {
    if (!n.readYn) { try { await markRead(n.id); } catch { /* noop */ } }
    if (n.bookId) navigate(`/books/${n.bookId}`);
  }
  async function onReadAll() {
    try { await markAllRead(); load(); } catch { /* noop */ }
  }

  return (
    <div style={{ fontFamily: T.font, color: T.text, background: T.bg, minHeight: '100%' }}>
      <div style={{ maxWidth: 760, margin: '0 auto', padding: isMobile ? '22px 16px 48px' : '34px 40px 56px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 18 }}>
          <h1 style={{ margin: 0, fontSize: isMobile ? 23 : 28, fontWeight: 800, color: T.ink, letterSpacing: '-0.025em' }}>알림</h1>
          {unread > 0 && (
            <button onClick={onReadAll} style={{ fontSize: 13, color: T.text, fontWeight: 600, background: 'none', border: 'none', cursor: 'pointer' }}>모두 읽음</button>
          )}
        </div>

        <div style={{ display: 'flex', gap: 8, marginBottom: 18 }}>
          {[['ALL', `전체 ${items.length}`], ['UNREAD', `안읽음 ${unread}`]].map(([k, lab]) => (
            <button key={k} onClick={() => setFilter(k)} style={{ padding: '8px 16px', borderRadius: T.radius.pill, fontSize: 13.5, fontWeight: 600, cursor: 'pointer', border: filter === k ? 'none' : `1px solid ${T.border}`, background: filter === k ? T.ink : T.surface, color: filter === k ? T.inkText : T.text }}>
              {lab}
            </button>
          ))}
        </div>

        {shown.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '56px 16px', background: T.surface, borderRadius: 16, border: `1px solid ${T.borderSoft}` }}>
            <div style={{ width: 52, height: 52, borderRadius: 15, background: '#e9f7f1', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 24, margin: '0 auto 14px' }}>🔔</div>
            <div style={{ fontSize: 15, fontWeight: 700, color: T.textStrong }}>알림이 없어요</div>
            <div style={{ fontSize: 13, color: T.muted, marginTop: 6 }}>새 소식이 오면 여기에 모여요.</div>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {shown.map((n) => (
              <button
                key={n.id}
                data-testid="notif-row"
                onClick={() => onItem(n)}
                style={{ display: 'flex', gap: 13, alignItems: 'center', textAlign: 'left', padding: '16px 18px', borderRadius: 13, cursor: 'pointer', border: `1px solid ${T.borderSoft}`, background: n.readYn ? T.surface : T.tint }}
              >
                <span style={{ width: 40, height: 40, borderRadius: 11, background: KIND_ICON_BG[n.kindCd] || T.tint, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 18, flexShrink: 0 }}>
                  {KIND_ICON[n.kindCd] || '🔔'}
                </span>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 13.5, color: T.textStrong, lineHeight: 1.5 }}>
                    <b>{n.title || '새 소식'}</b>{KIND_SUFFIX[n.kindCd] || ' 소식이 있어요.'}
                  </div>
                  <span style={{ display: 'block', fontSize: 12, color: T.muted, marginTop: 4 }}>{KIND_LABEL[n.kindCd] || '알림'}</span>
                </div>
                {!n.readYn && <span style={{ width: 8, height: 8, borderRadius: T.radius.pill, background: 'oklch(0.7 0.12 184)', flexShrink: 0 }} />}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
