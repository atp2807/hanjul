import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';

import { useAuth } from '../auth/AuthContext';
import { useIsMobile } from '../hooks/useIsMobile';
import { applyCampaign, getCampaign, getMyApplications } from '../services/api/campaigns';
import { getStoreDetail } from '../services/api/books';
import { coverGradient, T } from '../theme';
import { Icon } from '../components/Icon';

function Cond({ label, value }) {
  return (
    <div style={{ background: T.surface, borderRadius: 13, padding: '16px 18px' }}>
      <div style={{ fontSize: 12, color: T.muted, marginBottom: 5 }}>{label}</div>
      <div style={{ fontSize: 14, fontWeight: 700, color: T.textStrong }}>{value}</div>
    </div>
  );
}

export function CampaignDetailPage() {
  const { id } = useParams();
  const { user } = useAuth();
  const navigate = useNavigate();
  const isMobile = useIsMobile();
  const [c, setC] = useState(null);
  const [book, setBook] = useState(null);
  const [applied, setApplied] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');

  useEffect(() => {
    getCampaign(id)
      .then((camp) => {
        setC(camp);
        getStoreDetail(camp.bookId).then(setBook).catch(() => {});
      })
      .catch(() => setC(false));
    if (user) getMyApplications().then((r) => setApplied(r.items.some((a) => a.campaignId === id))).catch(() => {});
  }, [id, user]);

  async function onApply() {
    if (!user) { navigate('/login'); return; }
    setBusy(true); setErr('');
    try {
      await applyCampaign(id);
      setApplied(true);
    } catch (e) {
      if (e.status === 409) setErr('마감된 모집이에요.');
      else if (e.status === 403) setErr('서평단 참여 제한 기간이에요. 내 활동에서 해제일을 확인하세요.');
      else setErr('신청에 실패했어요.');
    } finally {
      setBusy(false);
    }
  }

  if (c === false) return <div style={{ padding: 60, textAlign: 'center', color: T.muted, fontFamily: T.font }}>캠페인을 찾을 수 없어요.</div>;
  if (!c) return <div style={{ padding: 60, textAlign: 'center', color: T.muted, fontFamily: T.font }}>불러오는 중…</div>;

  const pct = c.slots ? Math.round((c.filled / c.slots) * 100) : 0;
  const reviewDur = `증정본 수령 후 ${c.reviewDays}일`;

  return (
    <div style={{ fontFamily: T.font, color: T.text, background: T.bg, minHeight: '100%' }}>
      <div style={{ maxWidth: 1080, margin: '0 auto', padding: isMobile ? '20px 18px 48px' : '30px 40px 56px' }}>
        <div style={{ fontSize: 13, color: T.muted, marginBottom: 22 }}>
          <span onClick={() => navigate('/reviewers')} style={{ cursor: 'pointer' }}>서평단</span> &nbsp;›&nbsp; <span style={{ color: T.text }}>{c.bookTitle}</span>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : '1fr 360px', gap: isMobile ? 24 : 36, alignItems: 'start' }}>
          {/* 좌: 책 + 조건 */}
          <div>
            <div style={{ aspectRatio: '16 / 8', borderRadius: 18, background: coverGradient(c.bookTitle || c.id), display: 'flex', alignItems: 'flex-end', padding: 28, position: 'relative', overflow: 'hidden' }}>
              <span style={{ position: 'absolute', top: 16, left: 16, padding: '5px 12px', background: 'rgba(255,255,255,0.92)', borderRadius: T.radius.pill, fontSize: 12, fontWeight: 800, color: T.ink }}>● 리뷰어 모집중</span>
              <span style={{ color: '#eaf6f2', fontSize: 30, fontWeight: 800, letterSpacing: '-0.02em' }}>{c.bookTitle}</span>
            </div>
            <h1 style={{ margin: '22px 0 8px', fontSize: 26, fontWeight: 800, color: T.ink, letterSpacing: '-0.02em' }}>{c.bookTitle}</h1>
            {book?.subtitle && <div style={{ fontSize: 15, color: T.text, fontWeight: 600, marginBottom: 20 }}>{book.subtitle}</div>}
            {book?.description && <p style={{ margin: '0 0 26px', fontSize: 15, lineHeight: 1.85, color: T.textSoft }}>{book.description}</p>}

            <h3 style={{ margin: '0 0 14px', fontSize: 17, fontWeight: 800, color: T.textStrong }}>신청 조건 · 의무</h3>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 22 }}>
              <Cond label="리뷰 기한" value={reviewDur} />
              <Cond label="최소 분량" value={c.minChars > 0 ? `${c.minChars}자 이상` : '제한 없음'} />
              <Cond label="증정본" value={`${c.slots}부`} />
              <Cond label="공개 의무" value="서평단 라벨 표기" />
            </div>
            <div style={{ background: T.tint, border: `1px solid #cfe7df`, borderRadius: 14, padding: '18px 20px', display: 'flex', gap: 12 }}>
              <span style={{ flexShrink: 0, marginTop: 1 }}><Icon name="info" size={18} stroke="#2f8a6f" /></span>
              <p style={{ margin: 0, fontSize: 13.5, lineHeight: 1.7, color: T.text }}>
                서평단 증정본으로 작성한 리뷰에는 <b style={{ color: T.ink }}>‘서평단’ 라벨</b>이 자동으로 붙습니다. 대가성 표기는 법적 공개 의무이며, 솔직한 평가를 권장해요.
              </p>
            </div>
          </div>

          {/* 우: 신청 박스 */}
          <div style={{ background: T.surface, borderRadius: 20, padding: 26, position: 'sticky', top: 20 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, color: T.text, marginBottom: 8 }}>
              <span>남은 증정본</span>
              <span style={{ color: c.remaining > 0 ? T.text : '#e0654f', fontWeight: 700 }}>{c.statusCd === 'OPEN' ? '모집중' : '마감'}</span>
            </div>
            <div style={{ fontSize: 24, fontWeight: 800, color: T.ink, marginBottom: 8 }}>
              {c.remaining}부 <span style={{ fontSize: 14, fontWeight: 500, color: '#9bb4bc' }}>/ {c.slots}부</span>
            </div>
            <div style={{ height: 8, background: T.borderSoft, borderRadius: T.radius.pill, overflow: 'hidden', marginBottom: 22 }}>
              <div style={{ width: `${pct}%`, height: '100%', background: 'oklch(0.7 0.11 188)' }} />
            </div>

            {applied ? (
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6, padding: 15, background: T.tint, color: '#2f8a6f', borderRadius: 13, fontSize: 15, fontWeight: 700, border: `1px solid #cfe7df` }}><Icon name="check" size={18} stroke="#2f8a6f" /> 신청 완료</div>
            ) : (
              <button onClick={onApply} disabled={busy || c.statusCd !== 'OPEN'} style={{ width: '100%', padding: 15, background: c.statusCd === 'OPEN' ? T.ink : '#9bb4bc', color: T.inkText, border: 'none', borderRadius: 13, fontSize: 15, fontWeight: 700, cursor: c.statusCd === 'OPEN' ? 'pointer' : 'default' }}>
                {c.statusCd === 'OPEN' ? (busy ? '신청 중…' : '리뷰어 신청하기') : '마감된 모집'}
              </button>
            )}
            {err && <div style={{ color: '#e0654f', fontSize: 12.5, textAlign: 'center', marginTop: 10 }}>{err}</div>}
            <div style={{ fontSize: 12, color: '#9bb4bc', textAlign: 'center', marginTop: 10 }}>배정 결과는 알림으로 안내돼요.</div>

            <div style={{ height: 1, background: T.borderSoft, margin: '20px 0' }} />
            <div style={{ fontSize: 13, fontWeight: 700, color: T.textStrong, marginBottom: 12 }}>신청하면 지켜야 해요</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10, fontSize: 13, color: T.textSoft }}>
              <div style={{ display: 'flex', gap: 9, alignItems: 'center' }}><Icon name="check" size={15} stroke="#2f8a6f" /> {c.reviewDays}일 안에 리뷰 작성</div>
              <div style={{ display: 'flex', gap: 9, alignItems: 'center' }}><Icon name="check" size={15} stroke="#2f8a6f" /> {c.minChars > 0 ? `${c.minChars}자 이상 ` : ''}솔직한 평가</div>
              <div style={{ display: 'flex', gap: 9, alignItems: 'center' }}><Icon name="check" size={15} stroke="#2f8a6f" /> 서평단 라벨 유지</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
