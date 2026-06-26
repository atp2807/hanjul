import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { useAuth } from '../auth/AuthContext';
import { cancelApplication, dday, getMyApplications } from '../services/api/campaigns';
import { coverGradient, T } from '../theme';

const STATUS = {
  PENDING: { label: '신청 대기', fg: '#c79318', bg: '#fff3da' },
  ASSIGNED: { label: '배정됨', fg: '#2f8a6f', bg: '#e3f3ec' },
  COMPLETED: { label: '리뷰 완료', fg: T.text, bg: '#eef4f1' },
};

function StatCard({ label, value, sub, dark }) {
  return (
    <div style={{ background: dark ? 'linear-gradient(140deg,#0e4a5c,#1d7e8e)' : T.surface, borderRadius: 18, padding: '22px 24px' }}>
      <div style={{ fontSize: 13, color: dark ? T.inkSoft : T.muted }}>{label}</div>
      <div style={{ fontSize: 24, fontWeight: 800, color: dark ? '#fff' : T.ink, marginTop: 6 }}>{value}</div>
      {sub && <div style={{ fontSize: 12, color: dark ? T.inkSoft : '#2f8a6f', marginTop: 6 }}>{sub}</div>}
    </div>
  );
}

export function ReviewerActivityPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [items, setItems] = useState(null);
  const [filter, setFilter] = useState('ALL');

  function load() {
    getMyApplications().then((r) => setItems(r.items)).catch(() => setItems([]));
  }
  useEffect(() => { if (user) load(); }, [user]);

  if (!user) return <div style={{ padding: 60, textAlign: 'center', color: T.muted, fontFamily: T.font }}>로그인이 필요해요.</div>;
  if (items === null) return <div style={{ padding: 60, textAlign: 'center', color: T.muted, fontFamily: T.font }}>불러오는 중…</div>;

  const assigned = items.filter((a) => a.statusCd === 'ASSIGNED');
  const completed = items.filter((a) => a.statusCd === 'COMPLETED');
  const pending = items.filter((a) => a.statusCd === 'PENDING');
  const received = assigned.length + completed.length;
  const rate = received ? Math.round((completed.length / received) * 100) : null;

  const counts = { ALL: items.length, PENDING: pending.length, ASSIGNED: assigned.length, COMPLETED: completed.length };
  const shown = filter === 'ALL' ? items : items.filter((a) => a.statusCd === filter);

  async function onCancel(a) {
    try { await cancelApplication(a.campaignId); load(); } catch { /* noop */ }
  }

  return (
    <div style={{ fontFamily: T.font, color: T.text, background: T.bg, minHeight: '100%' }}>
      <div style={{ maxWidth: 1180, margin: '0 auto', padding: '34px 40px 56px' }}>
        <h1 style={{ margin: '0 0 22px', fontSize: 28, fontWeight: 800, color: T.ink, letterSpacing: '-0.025em' }}>내 서평단 활동</h1>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: 16, marginBottom: 28 }}>
          <StatCard dark label="완료율" value={rate === null ? '—' : `${rate}%`} sub={received ? `${received}건 중 ${completed.length}건 완료` : '아직 없음'} />
          <StatCard label="받은 증정본" value={`${received}권`} />
          <StatCard label="진행 중" value={`${assigned.length}건`} sub={assigned.length ? '리뷰 작성 대기' : null} />
          <StatCard label="신청 대기" value={`${pending.length}건`} />
        </div>

        <div style={{ display: 'flex', gap: 8, marginBottom: 20 }}>
          {[['ALL', '전체'], ['PENDING', '대기'], ['ASSIGNED', '배정'], ['COMPLETED', '완료']].map(([k, lab]) => (
            <button key={k} onClick={() => setFilter(k)} style={{ padding: '9px 18px', borderRadius: T.radius.pill, fontSize: 14, fontWeight: 600, cursor: 'pointer', border: filter === k ? 'none' : `1px solid ${T.border}`, background: filter === k ? T.ink : T.surface, color: filter === k ? T.inkText : T.text }}>
              {lab} {counts[k]}
            </button>
          ))}
        </div>

        {shown.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '56px 16px', background: T.surface, borderRadius: 16, border: `1px solid ${T.borderSoft}` }}>
            <div style={{ width: 52, height: 52, borderRadius: 15, background: '#e9f7f1', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 24, margin: '0 auto 14px' }}>📭</div>
            <div style={{ fontSize: 15, fontWeight: 700, color: T.textStrong }}>아직 활동이 없어요</div>
            <div style={{ fontSize: 13, color: T.muted, marginTop: 6 }}>관심 있는 책의 서평단에 신청해 보세요.</div>
            <button onClick={() => navigate('/reviewers')} style={{ marginTop: 14, padding: '9px 18px', background: T.ink, color: T.inkText, border: 'none', borderRadius: 10, fontSize: 12.5, fontWeight: 700, cursor: 'pointer' }}>둘러보기</button>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {shown.map((a) => {
              const st = STATUS[a.statusCd] || STATUS.PENDING;
              const d = a.statusCd === 'ASSIGNED' ? dday(a.deadlineAt) : null;
              const urgent = d && (d === 'D-day' || d === 'D-1' || d === '마감');
              return (
                <div key={a.id} style={{ display: 'flex', alignItems: 'center', gap: 16, padding: 16, background: T.surface, borderRadius: 14, border: `1px solid ${T.borderSoft}` }}>
                  <div style={{ width: 44, height: 62, borderRadius: 7, background: coverGradient(a.bookTitle || a.bookId), flexShrink: 0 }} />
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 14.5, fontWeight: 700, color: T.textStrong }}>{a.bookTitle || '제목 없음'}</div>
                    <div style={{ fontSize: 12.5, color: T.muted, marginTop: 3 }}>
                      {a.statusCd === 'ASSIGNED' && `리뷰 기한 ${d} · 증정본 수령 완료`}
                      {a.statusCd === 'PENDING' && '배정 결과를 기다리는 중'}
                      {a.statusCd === 'COMPLETED' && '리뷰 게시됨'}
                    </div>
                  </div>
                  <span style={{ padding: '5px 12px', borderRadius: T.radius.pill, fontSize: 12, fontWeight: 700, color: urgent ? '#e0654f' : st.fg, background: urgent ? '#fdeeea' : st.bg }}>
                    {st.label}{urgent && a.statusCd === 'ASSIGNED' ? ' · 마감임박' : ''}
                  </span>
                  {a.statusCd === 'PENDING' ? (
                    <button onClick={() => onCancel(a)} style={{ padding: '9px 16px', background: T.tint, color: T.ink, border: 'none', borderRadius: 10, fontSize: 13, fontWeight: 700, minWidth: 88, cursor: 'pointer' }}>신청 취소</button>
                  ) : (
                    <button onClick={() => navigate(a.statusCd === 'ASSIGNED' ? `/campaigns/${a.campaignId}/review` : `/books/${a.bookId}`)} style={{ padding: '9px 16px', background: a.statusCd === 'ASSIGNED' ? T.ink : T.tint, color: a.statusCd === 'ASSIGNED' ? T.inkText : T.ink, border: 'none', borderRadius: 10, fontSize: 13, fontWeight: 700, minWidth: 88, cursor: 'pointer' }}>
                      {a.statusCd === 'ASSIGNED' ? '리뷰 쓰기' : '리뷰 보기'}
                    </button>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
