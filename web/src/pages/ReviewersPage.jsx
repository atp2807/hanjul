import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { useApiQuery } from '@hanjul/lib';

import { useAuth } from '../auth/AuthContext';
import { useIsMobile } from '../hooks/useIsMobile';
import { dday, listOpenCampaigns } from '../services/api/campaigns';
import { coverGradient, T } from '../theme';
import { EmptyState } from '../components/EmptyState';
import { ErrorNotice } from '../components/ui';
import { Icon } from '../components/Icon';

function Stat({ value, label }) {
  return (
    <div>
      <div style={{ fontSize: 24, fontWeight: 800, color: T.ink }}>{value}</div>
      <div style={{ fontSize: 13, color: T.muted, marginTop: 2 }}>{label}</div>
    </div>
  );
}

function CampaignCard({ c, onClick }) {
  const pct = c.slots ? Math.round((c.filled / c.slots) * 100) : 0;
  const d = dday(null); // 목록 단계에선 마감일 정보 없음 → 진행률만
  return (
    <button
      onClick={onClick}
      style={{
        textAlign: 'left', padding: 0, cursor: 'pointer',
        background: T.surface, borderRadius: 16, overflow: 'hidden',
        border: `1px solid ${T.borderSoft}`,
      }}
    >
      <div
        style={{
          aspectRatio: '16 / 9', background: coverGradient(c.bookTitle || c.id),
          position: 'relative', display: 'flex', alignItems: 'flex-end', padding: 14,
        }}
      >
        <span style={{ position: 'absolute', top: 10, left: 10, padding: '4px 10px', background: 'rgba(255,255,255,0.92)', borderRadius: T.radius.pill, fontSize: 11, fontWeight: 800, color: T.ink }}>● 모집중</span>
        <span style={{ color: '#eaf6f2', fontSize: 16, fontWeight: 700, lineHeight: 1.25 }}>{c.bookTitle || '제목 없음'}</span>
      </div>
      <div style={{ padding: '16px 18px' }}>
        {c.category && <div style={{ fontSize: 12.5, color: T.muted, marginBottom: 10 }}>{c.category}</div>}
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, color: T.text, marginBottom: 6 }}>
          <span>남은 증정본 <b style={{ color: T.ink }}>{c.remaining}부</b></span>
          {d && <span style={{ fontWeight: 600 }}>{d}</span>}
        </div>
        <div style={{ height: 6, background: T.borderSoft, borderRadius: T.radius.pill, overflow: 'hidden' }}>
          <div style={{ width: `${pct}%`, height: '100%', background: 'oklch(0.7 0.11 188)' }} />
        </div>
        <span style={{ display: 'block', textAlign: 'center', marginTop: 14, padding: 11, background: T.ink, color: T.inkText, borderRadius: 11, fontSize: 13.5, fontWeight: 700 }}>리뷰어 신청</span>
      </div>
    </button>
  );
}

export function ReviewersPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const isMobile = useIsMobile();
  const [genre, setGenre] = useState(null); // null = 전체

  const { data, loading, error, reload } = useApiQuery(() => listOpenCampaigns(genre), [genre]);
  const items = loading ? null : (data?.items ?? null);

  const remaining = (items || []).reduce((s, c) => s + (c.remaining || 0), 0);

  return (
    <div style={{ fontFamily: T.font, color: T.text, background: T.bg, minHeight: '100%' }}>
      {/* 히어로 */}
      <section style={{ padding: isMobile ? '32px 20px 36px' : '64px 48px 52px', background: 'linear-gradient(180deg,#eaf7f3 0%,#f3faf8 78%)' }}>
        <div style={{ maxWidth: 1180, margin: '0 auto' }}>
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: 8, padding: '7px 15px', background: T.surface, border: `1px solid #cfe7df`, borderRadius: T.radius.pill, fontSize: 13, fontWeight: 700, color: '#297961', marginBottom: 24 }}>
            출간 전, 먼저 읽는 사람들
          </div>
          <h1 style={{ margin: 0, fontSize: isMobile ? 32 : 48, lineHeight: 1.15, fontWeight: 800, letterSpacing: '-0.035em', color: T.ink }}>
            공짜로 신간 받고,<br />먼저 읽고, 리뷰하세요
          </h1>
          <p style={{ margin: '22px 0 0', maxWidth: 480, fontSize: 17, lineHeight: 1.65, color: T.text }}>
            한줄 서평단에 신청하면 출간 전 증정본을 받아 누구보다 먼저 읽고, 솔직한 리뷰를 남길 수 있어요. 좋은 리뷰어에겐 더 많은 기회가 갑니다.
          </p>
          <div style={{ display: 'flex', gap: 12, marginTop: 30 }}>
            <a href="#feed" style={{ padding: '14px 26px', background: T.ink, color: T.inkText, borderRadius: 13, fontSize: 15, fontWeight: 700, textDecoration: 'none' }}>서평단 둘러보기</a>
            <button onClick={() => navigate(user ? '/studio/campaigns' : '/login')} style={{ padding: '14px 26px', background: T.surface, color: T.ink, border: `1px solid #d6e4de`, borderRadius: 13, fontSize: 15, fontWeight: 600, cursor: 'pointer' }}>작가라면 · 모집하기</button>
            <button onClick={() => navigate('/reviewers/business')} style={{ padding: '14px 20px', background: 'transparent', color: T.text, border: 'none', fontSize: 15, fontWeight: 600, cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: 4 }}>출판사세요? <Icon name="chevron" size={14} stroke="currentColor" /></button>
          </div>
          <div style={{ display: 'flex', gap: 34, marginTop: 36 }}>
            <Stat value={items ? items.length : '—'} label="모집중 캠페인" />
            <Stat value={items ? `${remaining}부` : '—'} label="남은 증정본" />
            {user && <button onClick={() => navigate('/reviewer/activity')} style={{ alignSelf: 'flex-end', background: 'none', border: 'none', color: T.ink, fontWeight: 700, fontSize: 14, cursor: 'pointer', textDecoration: 'underline', display: 'inline-flex', alignItems: 'center', gap: 3 }}>내 서평단 활동 <Icon name="chevron" size={13} stroke="currentColor" /></button>}
          </div>
        </div>
      </section>

      {/* 모집 피드 */}
      <section id="feed" style={{ maxWidth: 1180, margin: '0 auto', padding: isMobile ? '24px 18px 48px' : '34px 40px 64px' }}>
        <h2 style={{ margin: '0 0 6px', fontSize: 26, fontWeight: 800, color: T.ink, letterSpacing: '-0.025em' }}>서평단 모집</h2>
        <div style={{ fontSize: 14, color: T.muted, marginBottom: 18 }}>출간 전 증정본을 받고 먼저 리뷰할 책을 골라보세요.</div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 24 }}>
          {[['전체', null], ['소설', '소설'], ['에세이', '에세이'], ['시', '시'], ['자기계발', '자기계발'], ['경제·경영', '경제·경영']].map(([lab, val]) => {
            const on = genre === val;
            return (
              <button key={lab} onClick={() => setGenre(val)} style={{ padding: '9px 16px', borderRadius: T.radius.pill, fontSize: 14, fontWeight: 600, cursor: 'pointer', border: on ? 'none' : `1px solid #e0ebe6`, background: on ? T.ink : T.surface, color: on ? T.inkText : T.text }}>
                {lab}
              </button>
            );
          })}
        </div>
        {error ? (
          <ErrorNotice message="모집 목록을 불러오지 못했어요." onRetry={reload} style={{ margin: '24px 0' }} />
        ) : items === null ? (
          <div style={{ color: T.muted, padding: '40px 0' }}>불러오는 중…</div>
        ) : items.length === 0 ? (
          <EmptyState icon="search" title="모집 중인 캠페인이 없어요" desc="새 서평단이 열리면 곧 여기에 표시돼요." />
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr 1fr' : 'repeat(4, 1fr)', gap: isMobile ? 12 : 20 }}>
            {items.map((c) => (
              <CampaignCard key={c.id} c={c} onClick={() => navigate(`/campaigns/${c.id}`)} />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
