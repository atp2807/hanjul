import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { useAuth } from '../auth/AuthContext';
import { useIsMobile } from '../hooks/useIsMobile';
import { assignReviewer, closeCampaign, createCampaign, getApplicants, getMyCampaigns } from '../services/api/campaigns';
import { getMyBooks } from '../services/api/studio';
import { coverGradient, T } from '../theme';

function Stat({ label, value, sub }) {
  return (
    <div style={{ background: T.surface, borderRadius: 18, padding: '22px 24px' }}>
      <div style={{ fontSize: 13, color: T.muted }}>{label}</div>
      <div style={{ fontSize: 28, fontWeight: 800, color: T.ink, marginTop: 6, letterSpacing: '-0.02em' }}>{value}</div>
      {sub && <div style={{ fontSize: 12, color: '#2f8a6f', fontWeight: 600, marginTop: 6 }}>{sub}</div>}
    </div>
  );
}

const STATUS = {
  OPEN: { label: '모집중', fg: '#2f8a6f', bg: '#e3f3ec' },
  CLOSED: { label: '리뷰중', fg: '#c79318', bg: '#fff3da' },
};

function Applicants({ campaignId, onAssigned }) {
  const [list, setList] = useState(null);
  useEffect(() => { getApplicants(campaignId).then((r) => setList(r.items)).catch(() => setList([])); }, [campaignId]);
  if (list === null) return <div style={{ padding: 14, color: T.muted, fontSize: 13 }}>신청자 불러오는 중…</div>;
  if (list.length === 0) return <div style={{ padding: 14, color: T.muted, fontSize: 13 }}>아직 신청자가 없어요.</div>;

  async function assign(applicantId) {
    try { await assignReviewer(campaignId, applicantId); onAssigned(); } catch { /* noop */ }
  }
  const ST = { PENDING: '신청', ASSIGNED: '배정됨', COMPLETED: '리뷰완료' };
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8, padding: '8px 0 14px' }}>
      {list.map((a) => (
        <div key={a.id} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '10px 14px', background: T.bg, borderRadius: 11 }}>
          <span style={{ width: 30, height: 30, borderRadius: T.radius.pill, background: 'linear-gradient(140deg,#1d7e8e,#2aa0a8)' }} />
          <span style={{ flex: 1, fontSize: 14, fontWeight: 600, color: T.textStrong }}>{a.applicantName || '리뷰어'}</span>
          <span style={{ fontSize: 12.5, color: T.muted }}>{ST[a.statusCd] || a.statusCd}</span>
          {a.statusCd === 'PENDING' && (
            <button onClick={() => assign(a.applicantId)} style={{ padding: '7px 14px', background: T.ink, color: T.inkText, border: 'none', borderRadius: 9, fontSize: 12.5, fontWeight: 700, cursor: 'pointer' }}>배정</button>
          )}
        </div>
      ))}
    </div>
  );
}

function CreatePanel({ books, onClose, onCreated }) {
  const isMobile = useIsMobile();
  const [bookId, setBookId] = useState(books[0]?.id || '');
  const [slots, setSlots] = useState(10);
  const [reviewDays, setReviewDays] = useState(14);
  const [minChars, setMinChars] = useState(300);
  const [busy, setBusy] = useState(false);

  async function submit() {
    if (!bookId) return;
    setBusy(true);
    try { await createCampaign({ bookId, slots, reviewDays, minChars }); onCreated(); }
    finally { setBusy(false); }
  }
  const inp = { padding: '12px 14px', background: T.bg, border: `1px solid #dfeae5`, borderRadius: 11, fontSize: 14, color: T.textStrong, fontFamily: T.font, width: '100%', boxSizing: 'border-box' };

  return (
    <div style={{ background: T.surface, borderRadius: 18, padding: 26, marginBottom: 24, border: `1px solid ${T.borderSoft}` }}>
      <div style={{ fontSize: 16, fontWeight: 800, color: T.textStrong, marginBottom: 18 }}>새 서평단 캠페인</div>
      {books.length === 0 ? (
        <div style={{ color: T.muted, fontSize: 14 }}>먼저 책을 출판해야 캠페인을 열 수 있어요.</div>
      ) : (
        <>
          <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : '1fr 1fr', gap: 16 }}>
            <label style={{ fontSize: 13, fontWeight: 600, color: T.text }}>책 선택
              <select value={bookId} onChange={(e) => setBookId(e.target.value)} style={{ ...inp, marginTop: 7 }}>
                {books.map((b) => <option key={b.id} value={b.id}>{b.title}</option>)}
              </select>
            </label>
            <label style={{ fontSize: 13, fontWeight: 600, color: T.text }}>증정본 수량
              <input type="number" min={1} value={slots} onChange={(e) => setSlots(Math.max(1, +e.target.value))} style={{ ...inp, marginTop: 7 }} />
            </label>
            <label style={{ fontSize: 13, fontWeight: 600, color: T.text }}>리뷰 기한(일)
              <input type="number" min={1} value={reviewDays} onChange={(e) => setReviewDays(Math.max(1, +e.target.value))} style={{ ...inp, marginTop: 7 }} />
            </label>
            <label style={{ fontSize: 13, fontWeight: 600, color: T.text }}>최소 분량(자)
              <input type="number" min={0} value={minChars} onChange={(e) => setMinChars(Math.max(0, +e.target.value))} style={{ ...inp, marginTop: 7 }} />
            </label>
          </div>
          <div style={{ display: 'flex', gap: 10, marginTop: 18, justifyContent: 'flex-end' }}>
            <button onClick={onClose} style={{ padding: '11px 20px', background: T.tint, color: T.ink, border: 'none', borderRadius: 11, fontSize: 13.5, fontWeight: 700, cursor: 'pointer' }}>취소</button>
            <button onClick={submit} disabled={busy} style={{ padding: '11px 22px', background: T.ink, color: T.inkText, border: 'none', borderRadius: 11, fontSize: 13.5, fontWeight: 700, cursor: 'pointer' }}>{busy ? '게시 중…' : '캠페인 게시'}</button>
          </div>
          <div style={{ fontSize: 11.5, color: '#9bb4bc', marginTop: 14 }}>증정본은 전자책으로 즉시 배포되어 인쇄·재고 비용이 없어요.</div>
        </>
      )}
    </div>
  );
}

export function CampaignStudioPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const isMobile = useIsMobile();
  const [camps, setCamps] = useState(null);
  const [books, setBooks] = useState([]);
  const [creating, setCreating] = useState(false);
  const [openRow, setOpenRow] = useState(null);

  function load() {
    getMyCampaigns().then((r) => setCamps(r.items)).catch(() => setCamps([]));
  }
  useEffect(() => {
    if (!user) return;
    load();
    getMyBooks().then((r) => setBooks((r.items || r).filter((b) => b.status === 'PUBLISHED'))).catch(() => setBooks([]));
  }, [user]);

  if (!user) return <div style={{ padding: 60, textAlign: 'center', color: T.muted, fontFamily: T.font }}>로그인이 필요해요.</div>;
  if (camps === null) return <div style={{ padding: 60, textAlign: 'center', color: T.muted, fontFamily: T.font }}>불러오는 중…</div>;

  const ongoing = camps.filter((c) => c.statusCd === 'OPEN').length;
  const applicants = camps.reduce((s, c) => s + c.applicants, 0);
  const assigned = camps.reduce((s, c) => s + c.filled, 0);
  const reviewed = camps.reduce((s, c) => s + c.reviewed, 0);

  return (
    <div style={{ fontFamily: T.font, color: T.text, background: T.bg, minHeight: '100%' }}>
      <div style={{ maxWidth: 1180, margin: '0 auto', padding: isMobile ? '22px 16px 48px' : '34px 40px 56px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 26 }}>
          <div>
            <h1 style={{ margin: 0, fontSize: 26, fontWeight: 800, color: T.ink, letterSpacing: '-0.025em' }}>서평단 관리</h1>
            <div style={{ fontSize: 14, color: T.muted, marginTop: 4 }}>진행 중인 캠페인과 리뷰 현황을 확인하세요.</div>
          </div>
          <button onClick={() => setCreating((v) => !v)} style={{ padding: '11px 20px', background: T.ink, color: T.inkText, border: 'none', borderRadius: 11, fontSize: 13.5, fontWeight: 700, cursor: 'pointer' }}>＋ 새 캠페인</button>
        </div>

        {creating && <CreatePanel books={books} onClose={() => setCreating(false)} onCreated={() => { setCreating(false); load(); }} />}

        <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr 1fr' : 'repeat(4,1fr)', gap: isMobile ? 12 : 16, marginBottom: 24 }}>
          <Stat label="진행 중 캠페인" value={ongoing} />
          <Stat label="총 신청자" value={`${applicants}명`} />
          <Stat label="배정 완료" value={`${assigned}명`} />
          <Stat label="리뷰 완료" value={`${reviewed}건`} sub={assigned ? `완료율 ${Math.round((reviewed / assigned) * 100)}%` : null} />
        </div>

        {camps.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '56px 16px', background: T.surface, borderRadius: 16, border: `1px solid ${T.borderSoft}` }}>
            <div style={{ fontSize: 15, fontWeight: 700, color: T.textStrong }}>아직 캠페인이 없어요</div>
            <div style={{ fontSize: 13, color: T.muted, marginTop: 6 }}>출판한 책으로 서평단을 열어 출간 첫 주에 리뷰를 쌓아보세요.</div>
          </div>
        ) : (
          <div style={{ background: T.surface, borderRadius: 18, padding: isMobile ? '4px 14px 12px' : '8px 26px 16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', padding: '16px 0', borderBottom: `1px solid ${T.borderSoft}`, fontSize: 12, color: '#9bb4bc', fontWeight: 700 }}>
              <span style={{ flex: 1 }}>캠페인</span><span style={{ width: 80 }}>상태</span><span style={{ width: isMobile ? 64 : 110, textAlign: 'center' }}>신청/배정</span>{!isMobile && <span style={{ width: 140 }}>리뷰 완료율</span>}<span style={{ width: 96, textAlign: 'right' }}> </span>
            </div>
            {camps.map((c) => {
              const st = STATUS[c.statusCd] || STATUS.OPEN;
              const rate = c.filled ? Math.round((c.reviewed / c.filled) * 100) : 0;
              const open = openRow === c.id;
              return (
                <div key={c.id} style={{ borderBottom: `1px solid #f3f7f5` }}>
                  <div style={{ display: 'flex', alignItems: 'center', padding: '15px 0' }}>
                    <div style={{ flex: 1, display: 'flex', alignItems: 'center', gap: 12 }}>
                      <div style={{ width: 32, height: 44, borderRadius: 5, background: coverGradient(c.bookTitle || c.id) }} />
                      <span style={{ fontSize: 14, fontWeight: 700, color: T.textStrong }}>{c.bookTitle || '제목 없음'}</span>
                    </div>
                    <span style={{ width: 80 }}><span style={{ padding: '4px 10px', background: st.bg, color: st.fg, borderRadius: T.radius.pill, fontSize: 12, fontWeight: 700 }}>{st.label}</span></span>
                    <span style={{ width: isMobile ? 64 : 110, textAlign: 'center', fontSize: 14, color: T.text }}>{c.applicants}/{c.filled}</span>
                    {!isMobile && (
                      <span style={{ width: 140, display: 'flex', alignItems: 'center', gap: 8 }}>
                        <span style={{ flex: 1, height: 6, background: T.borderSoft, borderRadius: T.radius.pill, overflow: 'hidden' }}>
                          <span style={{ display: 'block', width: `${rate}%`, height: '100%', background: 'oklch(0.7 0.11 188)' }} />
                        </span>
                        <span style={{ fontSize: 12, color: T.text, fontWeight: 600 }}>{rate}%</span>
                      </span>
                    )}
                    <span style={{ width: 96, textAlign: 'right', display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
                      <button onClick={() => setOpenRow(open ? null : c.id)} style={{ background: 'none', border: 'none', color: T.ink, fontSize: 12.5, fontWeight: 700, cursor: 'pointer' }}>{open ? '닫기' : '신청자'}</button>
                      {c.statusCd === 'OPEN' && (
                        <button onClick={() => closeCampaign(c.id).then(load).catch(() => {})} style={{ background: 'none', border: 'none', color: T.muted, fontSize: 12.5, fontWeight: 700, cursor: 'pointer' }}>마감</button>
                      )}
                    </span>
                  </div>
                  {open && <Applicants campaignId={c.id} onAssigned={load} />}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
