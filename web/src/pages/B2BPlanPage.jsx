import { useNavigate } from 'react-router-dom';

import { T } from '../theme';

const PLANS = [
  {
    name: 'Basic', price: '건당 결제', desc: '가끔 출간하는 출판사',
    feats: ['캠페인 1건', '증정본 최대 100부', '기본 리뷰어 매칭', '리뷰 현황 리포트'],
    cta: '건당 시작', dark: false,
  },
  {
    name: 'Growth', price: '월정액', desc: '매월 신간을 내는 출판사', badge: '가장 인기',
    feats: ['★ 캠페인 무제한', '증정본 월 1,000부', '우선 노출·타깃 매칭', '상세 분석 대시보드', '전담 매니저'],
    cta: '상담 신청', dark: true,
  },
  {
    name: 'Enterprise', price: '맞춤', desc: '대형 출판사·에이전시',
    feats: ['Growth 전체 포함', 'API·정산 연동', '맞춤 리뷰어 풀', '브랜드 캠페인 페이지', 'SLA·계약'],
    cta: '문의하기', dark: false,
  },
];

function PlanCard({ p }) {
  const fg = p.dark ? '#eafaf5' : T.ink;
  return (
    <div style={{ background: p.dark ? T.ink : T.surface, borderRadius: 22, padding: '34px 30px', position: 'relative', overflow: 'hidden', textAlign: 'left' }}>
      {p.dark && <div style={{ position: 'absolute', right: -50, top: -50, width: 160, height: 160, borderRadius: T.radius.pill, background: 'rgba(255,255,255,0.07)' }} />}
      {p.badge && <div style={{ display: 'inline-block', padding: '4px 12px', background: 'oklch(0.74 0.1 188)', color: '#06342c', borderRadius: T.radius.pill, fontSize: 11, fontWeight: 800, marginBottom: 14 }}>{p.badge}</div>}
      <div style={{ fontSize: 16, fontWeight: 800, color: fg }}>{p.name}</div>
      <div style={{ margin: '14px 0 4px', fontSize: 34, fontWeight: 800, color: p.dark ? '#fff' : T.ink, letterSpacing: '-0.02em' }}>{p.price}</div>
      <div style={{ fontSize: 13, color: p.dark ? '#84a89e' : T.muted, marginBottom: 24 }}>{p.desc}</div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12, fontSize: 14, color: p.dark ? '#d6ebe4' : T.textSoft }}>
        {p.feats.map((f, i) => (
          <div key={i} style={f.startsWith('★') ? { color: 'oklch(0.82 0.1 184)', fontWeight: 700 } : undefined}>{f.startsWith('★') ? f : `✓ ${f}`}</div>
        ))}
      </div>
      <span style={{ display: 'block', textAlign: 'center', padding: 13, background: p.dark ? 'oklch(0.74 0.1 188)' : T.tint, color: p.dark ? '#06342c' : T.ink, borderRadius: 12, fontSize: 14, fontWeight: p.dark ? 800 : 700, marginTop: 28 }}>{p.cta}</span>
    </div>
  );
}

export function B2BPlanPage() {
  const navigate = useNavigate();
  return (
    <div style={{ fontFamily: T.font, color: T.text, background: T.bg, minHeight: '100%' }}>
      <div style={{ padding: '50px 48px 60px', textAlign: 'center' }}>
        <div style={{ display: 'inline-block', padding: '6px 14px', background: '#e3f3ec', borderRadius: T.radius.pill, fontSize: 12.5, fontWeight: 700, color: '#2f8a6f', marginBottom: 18 }}>출판사 · 에이전시 전용</div>
        <h1 style={{ margin: '0 0 12px', fontSize: 34, fontWeight: 800, color: T.ink, letterSpacing: '-0.03em' }}>출간 첫 주에, 진짜 리뷰를 쌓으세요</h1>
        <p style={{ margin: '0 auto 14px', maxWidth: 560, fontSize: 16, lineHeight: 1.7, color: T.muted }}>
          개인 작가의 셀프 캠페인은 <b style={{ color: T.text }}>무료</b>예요. 출판사·에이전시를 위한 대량·관리형 서평단은 유료 플랜으로 제공합니다.
        </p>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 20, maxWidth: 1040, margin: '34px auto 0' }}>
          {PLANS.map((p) => <PlanCard key={p.name} p={p} />)}
        </div>
        <div style={{ marginTop: 36, fontSize: 14, color: T.muted }}>
          개인 작가세요? <span onClick={() => navigate('/studio/campaigns')} style={{ color: T.ink, fontWeight: 700, cursor: 'pointer', textDecoration: 'underline' }}>무료로 서평단 열기 →</span>
        </div>
      </div>
    </div>
  );
}
