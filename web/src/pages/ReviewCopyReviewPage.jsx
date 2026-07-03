import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';

import { useApiQuery } from '@hanjul/lib';

import { useAuth } from '../auth/AuthContext';
import { getCampaign, getMyApplications } from '../services/api/campaigns';
import { addReview } from '../services/api/reviews';
import { ErrorNotice } from '../components/ui';
import { Icon } from '../components/Icon';
import { Stars } from '../components/Stars';
import { T } from '../theme';

// deadlineAt(ISO) → "D-2 · 11:58:04" (남은 시간 실시간). false = 확인 실패(없음과 구분).
function countdown(deadlineAt, now) {
  if (deadlineAt === false) return '기한 확인 실패 — 새로고침해 주세요';
  if (!deadlineAt) return '기한 없음';
  let ms = new Date(deadlineAt).getTime() - now;
  if (ms <= 0) return '마감됨';
  const days = Math.floor(ms / 86400000); ms -= days * 86400000;
  const h = Math.floor(ms / 3600000); ms -= h * 3600000;
  const m = Math.floor(ms / 60000); ms -= m * 60000;
  const s = Math.floor(ms / 1000);
  const pad = (n) => String(n).padStart(2, '0');
  return `D-${days} · ${pad(h)}:${pad(m)}:${pad(s)}`;
}

export function ReviewCopyReviewPage() {
  const { id } = useParams(); // campaignId
  const { user } = useAuth();
  const navigate = useNavigate();
  const [deadline, setDeadline] = useState(null);
  const [rating, setRating] = useState(0);
  const [body, setBody] = useState('');
  const [now, setNow] = useState(Date.now());
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');

  const { data: camp, loading, error, reload } = useApiQuery(() => getCampaign(id), [id]);
  useEffect(() => {
    // 마감일 확인 실패를 '기한 없음'으로 둔갑시키면 리뷰어가 마감을 놓친다 — 반드시 구분 표시
    if (user) getMyApplications().then((r) => {
      const a = r.items.find((x) => x.campaignId === id);
      if (a) setDeadline(a.deadlineAt);
    }).catch(() => setDeadline(false));
  }, [id, user]);

  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, []);

  if (!user) return <div style={{ padding: 60, textAlign: 'center', color: T.muted, fontFamily: T.font }}>로그인이 필요해요.</div>;
  if (loading) return <div style={{ padding: 60, textAlign: 'center', color: T.muted, fontFamily: T.font }}>불러오는 중…</div>;
  if (error) {
    if (error.status === 404) return <div style={{ padding: 60, textAlign: 'center', color: T.muted, fontFamily: T.font }}>캠페인을 찾을 수 없어요.</div>;
    return (
      <div style={{ maxWidth: 560, margin: '60px auto', fontFamily: T.font }}>
        <ErrorNotice message="캠페인 정보를 불러오지 못했어요." onRetry={reload} />
      </div>
    );
  }

  const minChars = camp.minChars || 0;
  const enough = body.length >= minChars;
  const pct = minChars ? Math.min(100, Math.round((body.length / minChars) * 100)) : 100;

  async function submit() {
    if (!rating || !enough) return;
    setBusy(true); setErr('');
    try {
      await addReview(camp.bookId, rating, body);
      navigate(`/books/${camp.bookId}`);
    } catch (e) {
      setErr(e.status === 403 ? '리뷰 권한이 없어요(증정본 미수령).' : '제출에 실패했어요.');
      setBusy(false);
    }
  }

  return (
    <div style={{ fontFamily: T.font, color: T.text, background: T.bg, minHeight: '100%' }}>
      <div style={{ maxWidth: 820, margin: '0 auto', padding: '30px 40px 56px' }}>
        {/* 증정본 헤더 + 카운트다운 */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: T.ink, borderRadius: 16, padding: '18px 24px', marginBottom: 24 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <span style={{ padding: '5px 12px', background: 'oklch(0.74 0.1 188)', color: '#06342c', borderRadius: T.radius.pill, fontSize: 12, fontWeight: 800 }}>서평단 증정본</span>
            <span style={{ fontSize: 14, color: T.inkText, fontWeight: 600 }}>{camp.bookTitle}</span>
          </div>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: 11, color: T.inkSoft }}>리뷰 마감까지</div>
            <div style={{ fontSize: 18, fontWeight: 800, color: '#fff', fontVariantNumeric: 'tabular-nums' }}>{countdown(deadline, now)}</div>
          </div>
        </div>

        {/* 작성 폼 */}
        <div style={{ background: T.surface, borderRadius: 18, padding: '30px 32px' }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: T.text, marginBottom: 10 }}>별점</div>
          <div style={{ marginBottom: 24 }}>
            <Stars value={rating} onRate={setRating} size={30} gap={4} />
          </div>
          <div style={{ fontSize: 13, fontWeight: 700, color: T.text, marginBottom: 8 }}>리뷰</div>
          <textarea
            value={body}
            onChange={(e) => setBody(e.target.value)}
            placeholder="이 책을 솔직하게 평가해 주세요."
            style={{ width: '100%', boxSizing: 'border-box', background: T.bg, border: `1px solid #dfeae5`, borderRadius: 13, padding: 18, minHeight: 170, fontSize: 15, lineHeight: 1.9, color: '#2f4248', fontFamily: T.font, resize: 'vertical', outline: 'none' }}
          />
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 14, gap: 20 }}>
            <div style={{ flex: 1 }}>
              {minChars > 0 && (
                <>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, color: T.muted, marginBottom: 5 }}>
                    <span>최소 분량 {enough ? '충족' : ''}</span>
                    <span style={{ color: enough ? '#2f8a6f' : T.muted, fontWeight: 700 }}>{body.length} / {minChars}자</span>
                  </div>
                  <div style={{ height: 5, background: T.borderSoft, borderRadius: T.radius.pill, overflow: 'hidden' }}>
                    <div style={{ width: `${pct}%`, height: '100%', background: enough ? '#2f8a6f' : 'oklch(0.7 0.11 188)' }} />
                  </div>
                </>
              )}
            </div>
            <button onClick={submit} disabled={busy || !rating || !enough} style={{ padding: '13px 28px', background: !rating || !enough ? '#9bb4bc' : T.ink, color: T.inkText, border: 'none', borderRadius: 12, fontSize: 14, fontWeight: 700, cursor: !rating || !enough ? 'default' : 'pointer', whiteSpace: 'nowrap' }}>
              {busy ? '제출 중…' : '리뷰 제출'}
            </button>
          </div>
          {err && <div style={{ color: '#e0654f', fontSize: 12.5, marginTop: 10 }}>{err}</div>}
        </div>

        <div style={{ display: 'flex', gap: 10, marginTop: 16, padding: '14px 18px', background: T.tint, borderRadius: 13, fontSize: 13, color: T.text, lineHeight: 1.6, alignItems: 'flex-start' }}>
          <span style={{ flexShrink: 0, marginTop: 1 }}><Icon name="bookmark" size={16} stroke={T.ink} /></span>
          <div>제출하면 이 리뷰에 <b style={{ color: T.ink }}>‘서평단’ 라벨</b>이 표시돼요. 기한 내 미작성 시 신뢰도가 하락할 수 있어요.</div>
        </div>
      </div>
    </div>
  );
}
