import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { getNotifications, markAllRead, markRead } from '../services/api/notifications';
import { T } from '../theme';

const KIND_LABEL = { NEW_BOOK: '신간', REVISION: '개정판', ASSIGNED: '서평단', DUE_SOON: '마감 임박' };
const KIND_SUFFIX = {
  NEW_BOOK: '이(가) 출간됐어요.',
  REVISION: '의 개정판이 나왔어요.',
  ASSIGNED: ' 서평단에 배정됐어요. 증정본이 서재에 도착했어요.',
  DUE_SOON: ' 리뷰 마감이 다가와요. 잊지 말고 작성해 주세요.',
};
const KIND_ICON = { NEW_BOOK: '🚀', REVISION: '✏️', ASSIGNED: '🎁', DUE_SOON: '⏰' };
const KIND_ICON_BG = { NEW_BOOK: '#e3f3ec', REVISION: '#fff3da', ASSIGNED: '#e3f3ec', DUE_SOON: '#fdeeea' };

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
        style={{ position: 'relative', width: 36, height: 36, borderRadius: 999, border: `1px solid ${T.border}`, background: T.surface, fontSize: 16, lineHeight: 1, cursor: 'pointer' }}
      >
        🔔
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
          {items.length === 0 ? (
            <p style={{ padding: 28, textAlign: 'center', color: T.muted, fontSize: 13 }}>알림이 없어요.</p>
          ) : (
            items.map((n) => (
              <button
                key={n.id}
                data-testid="notif-item"
                onClick={() => openItem(n)}
                style={{ display: 'flex', gap: 14, width: '100%', textAlign: 'left', padding: '18px 24px', border: 'none', borderBottom: '1px solid #f3f7f5', background: n.readYn ? T.surface : T.bg, cursor: 'pointer', alignItems: 'flex-start' }}
              >
                <span style={{ width: 40, height: 40, borderRadius: 11, background: KIND_ICON_BG[n.kindCd] || T.tint, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 18, flexShrink: 0 }}>
                  {KIND_ICON[n.kindCd] || '🔔'}
                </span>
                <span style={{ flex: 1 }}>
                  <span style={{ display: 'block', fontSize: 14, color: T.textStrong, lineHeight: 1.5 }}>
                    <b>{n.title || '새 책'}</b> {KIND_SUFFIX[n.kindCd] || '소식이 있어요.'}
                  </span>
                  <span style={{ display: 'block', fontSize: 12, color: '#a8b5af', marginTop: 4 }}>{KIND_LABEL[n.kindCd] || '알림'}</span>
                </span>
                {!n.readYn && <span style={{ width: 8, height: 8, borderRadius: 999, background: T.accent, marginTop: 6, flexShrink: 0 }} />}
              </button>
            ))
          )}
        </div>
      )}
    </div>
  );
}
