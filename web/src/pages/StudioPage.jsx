import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';

import { useAuth } from '../auth/AuthContext';
import { updateProfile } from '../services/api/authors';
import { createBook, getMyBooks, getSales } from '../services/api/studio';
import { Icon } from '../components/Icon';
import { T } from '../theme';

export const STATUS_LABEL = { DRAFT: '초안', REVIEW: '심사중', PUBLISHED: '출판됨' };
const STATUS_PILL = {
  PUBLISHED: { bg: '#e3f3ec', fg: '#297961', text: '판매중' },
  DRAFT: { bg: '#fff3da', fg: '#8e6911', text: '초고' },
  REVIEW: { bg: '#e8eeff', fg: '#5b6da8', text: '심사중' },
};

export function StudioPage() {
  const { user, loading } = useAuth();
  const navigate = useNavigate();
  const [items, setItems] = useState([]);
  const [sales, setSales] = useState(null);
  const [title, setTitle] = useState('');
  const [fetching, setFetching] = useState(true);
  const [bio, setBio] = useState('');
  const [bioMsg, setBioMsg] = useState(null);

  useEffect(() => { setBio(user?.bio || ''); }, [user]);

  async function saveBio() {
    try {
      await updateProfile(bio);
      setBioMsg({ ok: true, text: '작가 소개를 저장했어요.' });
    } catch (e) {
      setBioMsg({ ok: false, text: `저장 실패: ${e.message}` });
    }
  }

  useEffect(() => {
    if (loading) return;
    if (!user) {
      setFetching(false);
      return;
    }
    Promise.all([getMyBooks(), getSales()])
      .then(([books, s]) => {
        setItems(books.items);
        setSales(s);
      })
      .finally(() => setFetching(false));
  }, [user, loading]);

  async function handleCreate(e) {
    e.preventDefault();
    if (!title.trim()) return;
    const { bookId } = await createBook(title.trim());
    navigate(`/studio/${bookId}`);
  }

  if (loading || fetching) return <Center>불러오는 중…</Center>;
  if (!user) return <Center>로그인이 필요해요.</Center>;

  const salesByBook = {};
  (sales?.books || []).forEach((b) => { salesByBook[b.bookId] = b; });

  return (
    <div style={{ maxWidth: 1080, margin: '0 auto', padding: '30px 40px 56px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 26, flexWrap: 'wrap', gap: 12 }}>
        <div>
          <h1 style={{ margin: 0, fontSize: 26, fontWeight: 800, color: T.ink, letterSpacing: '-0.025em' }}>
            안녕하세요, {user.displayName || '작가'}님
          </h1>
          <div style={{ fontSize: 14, color: T.muted, marginTop: 4 }}>이번 달 성과를 한눈에 살펴보세요.</div>
        </div>
        <Link to="/studio/campaigns" style={{ padding: '11px 18px', background: T.ink, color: T.inkText, borderRadius: 11, fontSize: 13.5, fontWeight: 700, textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: 7 }}><Icon name="bookmark" size={16} stroke={T.inkText} /> 서평단 관리</Link>
      </div>

      {sales && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16, marginBottom: 24 }}>
          <Link to="/settlement" style={{ textDecoration: 'none' }}>
            <Stat label="내 수익 (정산·출금 ›)" value={`${sales.totalPayout.toLocaleString()}원`} />
          </Link>
          <Stat label="판매 부수" value={`${sales.totalOrders.toLocaleString()}권`} />
          <Stat label="총 매출" value={`${sales.totalRevenue.toLocaleString()}원`} />
        </div>
      )}

      {/* 작가 소개 + 새 책 */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 16, marginBottom: 28 }}>
        <div style={{ background: T.surface, borderRadius: 18, padding: 22 }}>
          <div style={{ fontSize: 13, color: T.textMid, fontWeight: 600, marginBottom: 8 }}>작가 소개 (프로필에 노출)</div>
          <textarea
            data-testid="bio-input"
            value={bio}
            onChange={(e) => setBio(e.target.value)}
            rows={3}
            placeholder="독자에게 보일 작가 소개를 적어주세요"
            style={{ width: '100%', boxSizing: 'border-box', padding: 10, border: `1px solid ${T.border}`, borderRadius: 10, fontFamily: 'inherit', display: 'block', background: T.bg }}
          />
          <button onClick={saveBio} style={{ marginTop: 8, padding: '9px 16px', borderRadius: 10, border: `1px solid ${T.border}`, background: T.surface, color: T.textMid, fontWeight: 600, cursor: 'pointer' }}>소개 저장</button>
          {bioMsg && <span style={{ marginLeft: 10, fontSize: 13, color: bioMsg.ok ? '#297961' : 'crimson' }}>{bioMsg.text}</span>}
        </div>
        <div style={{ background: T.surface, borderRadius: 18, padding: 22 }}>
          <div style={{ fontSize: 13, color: T.textMid, fontWeight: 600, marginBottom: 8 }}>새 책 시작</div>
          <form onSubmit={handleCreate} style={{ display: 'flex', gap: 8 }}>
            <input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="새 책 제목"
              style={{ flex: 1, padding: '10px 12px', border: `1px solid ${T.border}`, borderRadius: 10, background: T.bg, fontFamily: 'inherit' }}
            />
            <button style={{ padding: '10px 16px', borderRadius: 10, background: T.ink, color: T.inkText, fontWeight: 700, border: 'none', cursor: 'pointer', whiteSpace: 'nowrap' }}>
              새 책 만들기
            </button>
          </form>
        </div>
      </div>

      {/* 내 책 테이블 */}
      <div style={{ background: T.surface, borderRadius: 18, padding: '8px 26px 14px' }}>
        <div style={{ display: 'flex', alignItems: 'center', padding: '16px 0', borderBottom: '1px solid #eef4f1', fontSize: 12, color: T.faint, fontWeight: 700 }}>
          <span style={{ flex: 1 }}>책</span><span style={{ width: 90 }}>상태</span>
          <span style={{ width: 90, textAlign: 'right' }}>판매</span><span style={{ width: 120, textAlign: 'right' }}>수익</span>
        </div>
        {items.length === 0 && <p style={{ color: T.muted, padding: '18px 0' }}>아직 쓴 책이 없어요. 위에서 만들어보세요.</p>}
        {items.map((b) => {
          const s = salesByBook[b.id];
          const pill = STATUS_PILL[b.status] || { bg: T.tint, fg: T.textMid, text: STATUS_LABEL[b.status] || b.status };
          return (
            <Link key={b.id} to={`/studio/${b.id}`} style={{ display: 'flex', alignItems: 'center', padding: '14px 0', borderBottom: '1px solid #f3f7f5', textDecoration: 'none', color: 'inherit' }}>
              <span style={{ flex: 1, fontSize: 14, fontWeight: 700, color: T.textStrong }}>{b.title}</span>
              <span style={{ width: 90 }}>
                <span style={{ padding: '4px 10px', background: pill.bg, color: pill.fg, borderRadius: 999, fontSize: 12, fontWeight: 700 }}>{pill.text}</span>
              </span>
              <span style={{ width: 90, textAlign: 'right', fontSize: 14, color: T.textMid }}>{s ? `${s.orderCount}권` : '—'}</span>
              <span style={{ width: 120, textAlign: 'right', fontSize: 14, fontWeight: 700, color: T.ink }}>{s ? `${s.payout.toLocaleString()}원` : '—'}</span>
            </Link>
          );
        })}
      </div>
    </div>
  );
}

function Stat({ label, value }) {
  return (
    <div style={{ background: T.surface, borderRadius: 18, padding: 24 }}>
      <div style={{ fontSize: 13, color: T.muted }}>{label}</div>
      <div style={{ fontSize: 30, fontWeight: 800, marginTop: 8, color: T.ink, letterSpacing: '-0.02em' }}>{value}</div>
    </div>
  );
}

function Center({ children }) {
  return <p style={{ textAlign: 'center', color: T.muted, padding: 40 }}>{children}</p>;
}
