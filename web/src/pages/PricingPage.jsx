import { useNavigate } from 'react-router-dom';

import { T } from '../theme';

const TIERS = [
  {
    name: '무료',
    price: '0원',
    note: '누구나 바로 시작',
    feats: ['✓ 글쓰기 에디터 무제한', '✓ 전자책 출판', '✓ 기본 서점 이용', '· 수익 배분 70%'],
    cta: '시작하기',
    dark: false,
    to: '/studio',
  },
  {
    name: '독자 멤버십',
    price: '9,900원',
    per: '/월',
    note: '무제한으로 읽고 싶다면',
    feats: ['✓ 멤버십 도서 무제한 읽기', '✓ 오프라인 다운로드', '✓ 광고 없는 리더', '✓ 신간 우선 열람'],
    cta: '멤버십 시작',
    dark: false,
  },
  {
    name: '작가 Pro',
    price: '19,900원',
    per: '/월',
    note: '본격적으로 펴내는 작가에게',
    feats: ['✓ 수익 배분 85%', '✓ 무제한 출판', '✓ 판매·유입 분석', '✓ 서점 우선 노출'],
    cta: 'Pro 시작',
    dark: true,
  },
];

export function PricingPage() {
  const navigate = useNavigate();

  return (
    <div style={{ padding: '54px 40px 64px', textAlign: 'center' }}>
      <h1 style={{ margin: '0 0 10px', fontSize: 34, fontWeight: 800, color: T.ink, letterSpacing: '-0.03em' }}>읽는 사람도, 쓰는 사람도</h1>
      <p style={{ margin: '0 auto 40px', maxWidth: 480, fontSize: 16, lineHeight: 1.7, color: T.muted }}>
        필요한 만큼만 쓰세요. 글을 펴내는 일은 언제나 무료로 시작할 수 있어요.
      </p>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: 20, maxWidth: 1040, margin: '0 auto', textAlign: 'left' }}>
        {TIERS.map((t) => (
          <div key={t.name} style={{ background: t.dark ? T.ink : T.surface, borderRadius: 22, padding: '34px 30px', position: 'relative', overflow: 'hidden' }}>
            {t.dark && <div style={{ position: 'absolute', right: -40, top: -40, width: 160, height: 160, borderRadius: 999, background: 'rgba(255,255,255,0.06)' }} />}
            <div style={{ fontSize: 16, fontWeight: 800, color: t.dark ? '#dff5ef' : T.ink }}>{t.name}</div>
            <div style={{ margin: '14px 0 6px', fontSize: 36, fontWeight: 800, color: t.dark ? '#eafaf5' : T.ink, letterSpacing: '-0.02em' }}>
              {t.price}
              {t.per && <span style={{ fontSize: 15, fontWeight: 600, color: t.dark ? '#9fc7bb' : '#a8b5af' }}>{t.per}</span>}
            </div>
            <div style={{ fontSize: 13, color: t.dark ? '#9fc7bb' : T.muted, marginBottom: 24 }}>{t.note}</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12, fontSize: 14, color: t.dark ? '#cfe9e1' : '#52615b' }}>
              {t.feats.map((f) => (
                <div key={f} style={f.startsWith('·') ? { color: t.dark ? '#7fae9f' : '#b6c4be' } : undefined}>{f}</div>
              ))}
            </div>
            <button
              onClick={() => (t.to ? navigate(t.to) : window.alert('곧 제공될 예정이에요.'))}
              style={{
                display: 'block', width: '100%', textAlign: 'center', padding: 13, marginTop: 28,
                background: t.dark ? '#eafaf5' : '#eef6f3', color: T.ink, border: 'none',
                borderRadius: 12, fontSize: 14, fontWeight: 700, cursor: 'pointer',
              }}
            >
              {t.cta}
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
