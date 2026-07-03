import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { KIND_ICON, KIND_ICON_BG, KIND_LABEL, KIND_SUFFIX } from '../notificationKinds';
import { getNotifications, markAllRead, markRead } from '../services/api/notifications';
import { T } from '../theme';
import { Icon } from './Icon';

// 헤더 알림함 — 안읽음 배지 + 드롭다운. 로그인 상태에서만 렌더.
export function NotificationBell() {
  const [items, setItems] = useState([]);
  const [unread, setUnread] = useState(0);
  const [open, setOpen] = useState(false);
  const [actionError, setActionError] = useState('');
  const navigate = useNavigate();
  const ref = useRef(null);

  const refresh = useCallback(() => {
    getNotifications()
      .then((d) => {
        setItems(d.items);
        setUnread(d.unreadCount);
      })
      .catch(() => {}); // 폴링 실패는 침묵 — 60초 뒤 재시도되고, 상세는 알림 페이지가 에러 표시
  }, []);

  // 최초 로드 + 60초 폴링 (신간 알림 도착 반영)
  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 60000);
    return () => clearInterval(t);
  }, [refresh]);

  // 바깥 클릭 시 닫기
  useEffect(() => {
    function onDoc(e) {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    }
    document.addEventListener('mousedown', onDoc);
    return () => document.removeEventListener('mousedown', onDoc);
  }, []);

  async function openItem(n) {
    if (!n.isRead) {
      // 읽음 표시 실패는 이동을 막지 않음 (안읽음으로 남아 다음에 다시 보임)
      await markRead(n.id).catch(() => {});
      refresh();
    }
    setOpen(false);
    if (n.bookId) navigate(`/books/${n.bookId}`);
  }

  async function onMarkAll() {
    setActionError('');
    try { await markAllRead(); }
    catch { setActionError('모두 읽음 처리에 실패했어요.'); return; }
    refresh();
  }

  return (
    <div ref={ref} style={{ position: 'relative' }}>
      <button
        data-testid="notif-bell"
        onClick={() => setOpen((v) => !v)}
        aria-label="알림"
        style={{ position: 'relative', width: 36, height: 36, borderRadius: 999, border: `1px solid ${T.border}`, background: T.surface, cursor: 'pointer', display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}
      >
        <Icon name="bell" size={19} stroke={T.textMid} />
        {unread > 0 && (
          <span
            data-testid="notif-badge"
            style={{ position: 'absolute', top: -4, right: -4, minWidth: 18, height: 18, padding: '0 5px', borderRadius: 9, background: '#e11d48', color: '#fff', fontSize: 11, fontWeight: 700, display: 'flex', alignItems: 'center', justifyContent: 'center', boxSizing: 'border-box' }}
          >
            {unread > 99 ? '99+' : unread}
          </span>
        )}
      </button>

      {open && (
        <div
          data-testid="notif-panel"
          style={{ position: 'absolute', right: 0, top: 44, width: 380, maxHeight: 460, overflowY: 'auto', background: T.surface, border: `1px solid ${T.border}`, borderRadius: 18, boxShadow: T.shadow, zIndex: 60 }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '20px 24px', borderBottom: '1px solid #eef4f1' }}>
            <h2 style={{ margin: 0, fontSize: 18, fontWeight: 800, color: T.ink }}>알림</h2>
            {unread > 0 && (
              <button onClick={onMarkAll} style={{ fontSize: 13, color: T.textMid, fontWeight: 600, background: 'none', border: 'none', cursor: 'pointer' }}>
                모두 읽음
              </button>
            )}
          </div>
          {actionError && (
            <div role="alert" style={{ padding: '10px 24px', fontSize: 12.5, fontWeight: 600, color: T.danger, background: T.dangerBg }}>{actionError}</div>
          )}
          {items.length === 0 ? (
            <p style={{ padding: 28, textAlign: 'center', color: T.muted, fontSize: 13 }}>알림이 없어요.</p>
          ) : (
            items.map((n) => (
              <button
                key={n.id}
                data-testid="notif-item"
                onClick={() => openItem(n)}
                style={{ display: 'flex', gap: 14, width: '100%', textAlign: 'left', padding: '18px 24px', border: 'none', borderBottom: '1px solid #f3f7f5', background: n.isRead ? T.surface : T.bg, cursor: 'pointer', alignItems: 'flex-start' }}
              >
                <span style={{ width: 40, height: 40, borderRadius: 11, background: KIND_ICON_BG[n.kind] || T.tint, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                  <Icon name={KIND_ICON[n.kind] || 'bell'} size={18} stroke="#143e4a" />
                </span>
                <span style={{ flex: 1 }}>
                  <span style={{ display: 'block', fontSize: 14, color: T.textStrong, lineHeight: 1.5 }}>
                    <b>{n.title || '새 책'}</b> {KIND_SUFFIX[n.kind] || '소식이 있어요.'}
                  </span>
                  <span style={{ display: 'block', fontSize: 12, color: '#a8b5af', marginTop: 4 }}>{KIND_LABEL[n.kind] || '알림'}</span>
                </span>
                {!n.isRead && <span style={{ width: 8, height: 8, borderRadius: 999, background: T.accent, marginTop: 6, flexShrink: 0 }} />}
              </button>
            ))
          )}
          <button
            onClick={() => { setOpen(false); navigate('/notifications'); }}
            style={{ display: 'block', width: '100%', padding: '14px 24px', border: 'none', borderTop: '1px solid #eef4f1', background: T.surface, color: T.ink, fontSize: 13, fontWeight: 700, cursor: 'pointer' }}
          >
            알림 전체보기
          </button>
        </div>
      )}
    </div>
  );
}
