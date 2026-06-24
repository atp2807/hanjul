import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { getNotifications, markAllRead, markRead } from '../services/api/notifications';

const KIND_LABEL = { NEW_BOOK: '신간' };

// 헤더 알림함 — 안읽음 배지 + 드롭다운. 로그인 상태에서만 렌더.
export function NotificationBell() {
  const [items, setItems] = useState([]);
  const [unread, setUnread] = useState(0);
  const [open, setOpen] = useState(false);
  const navigate = useNavigate();
  const ref = useRef(null);

  const refresh = useCallback(() => {
    getNotifications()
      .then((d) => {
        setItems(d.items);
        setUnread(d.unreadCount);
      })
      .catch(() => {});
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
    if (!n.readYn) {
      await markRead(n.id).catch(() => {});
      refresh();
    }
    setOpen(false);
    if (n.bookId) navigate(`/books/${n.bookId}`);
  }

  async function onMarkAll() {
    await markAllRead().catch(() => {});
    refresh();
  }

  return (
    <div ref={ref} style={{ position: 'relative' }}>
      <button
        data-testid="notif-bell"
        onClick={() => setOpen((v) => !v)}
        aria-label="알림"
        style={{ position: 'relative', padding: '6px 10px', borderRadius: 8, border: '1px solid #ddd', background: '#fff', fontSize: 16, lineHeight: 1 }}
      >
        🔔
        {unread > 0 && (
          <span
            data-testid="notif-badge"
            style={{ position: 'absolute', top: -6, right: -6, minWidth: 18, height: 18, padding: '0 5px', borderRadius: 9, background: '#e11d48', color: '#fff', fontSize: 11, fontWeight: 700, display: 'flex', alignItems: 'center', justifyContent: 'center', boxSizing: 'border-box' }}
          >
            {unread > 99 ? '99+' : unread}
          </span>
        )}
      </button>

      {open && (
        <div
          data-testid="notif-panel"
          style={{ position: 'absolute', right: 0, top: 40, width: 320, maxHeight: 400, overflowY: 'auto', background: '#fff', border: '1px solid #eee', borderRadius: 12, boxShadow: '0 8px 24px rgba(0,0,0,0.12)', zIndex: 20 }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 14px', borderBottom: '1px solid #f1f1f1' }}>
            <strong style={{ fontSize: 14 }}>알림</strong>
            {unread > 0 && (
              <button onClick={onMarkAll} style={{ fontSize: 12, color: '#2563eb', background: 'none', border: 'none', cursor: 'pointer' }}>
                모두 읽음
              </button>
            )}
          </div>
          {items.length === 0 ? (
            <p style={{ padding: 24, textAlign: 'center', color: '#999', fontSize: 13 }}>알림이 없어요.</p>
          ) : (
            items.map((n) => (
              <button
                key={n.id}
                data-testid="notif-item"
                onClick={() => openItem(n)}
                style={{ display: 'block', width: '100%', textAlign: 'left', padding: '12px 14px', border: 'none', borderBottom: '1px solid #f6f6f6', background: n.readYn ? '#fff' : '#f5f8ff', cursor: 'pointer' }}
              >
                <div style={{ fontSize: 12, color: '#2563eb', fontWeight: 600 }}>{KIND_LABEL[n.kindCd] || '알림'}</div>
                <div style={{ fontSize: 14, color: '#222', marginTop: 2 }}>
                  <strong>{n.title || '새 책'}</strong> 이(가) 출간됐어요.
                </div>
              </button>
            ))
          )}
        </div>
      )}
    </div>
  );
}
