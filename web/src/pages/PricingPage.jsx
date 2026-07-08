import { T } from '../theme';

// 수수료·정산 안내 (구 요금제 — 우리는 구독 티어가 아니라 판매 수수료(분배) 모델).
function Stat({ value, label, color }) {
  return (
    <div style={{ background: T.surface, borderRadius: 18, padding: 26, textAlign: 'center' }}>
      <div style={{ fontSize: 34, fontWeight: 800, color: color || T.ink, letterSpacing: '-0.02em' }}>{value}</div>
      <div style={{ fontSize: 13.5, color: T.muted, marginTop: 6 }}>{label}</div>
    </div>
  );
}

function ChannelCard({ title, desc, authorPct, authorLabel, platLabel, recommend }) {
  return (
    <div style={{ background: T.surface, borderRadius: 20, padding: '28px 30px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
        <div style={{ fontSize: 17, fontWeight: 800, color: T.ink }}>{title}</div>
        {recommend && <span style={{ padding: '4px 11px', background: '#e3f3ec', borderRadius: 999, fontSize: 12, fontWeight: 700, color: '#297961' }}>추천</span>}
      </div>
      <p style={{ margin: '0 0 20px', fontSize: 13.5, color: T.muted, lineHeight: 1.6 }}>{desc}</p>
      <div style={{ display: 'flex', height: 42, borderRadius: 11, overflow: 'hidden' }}>
        <div style={{ width: `${authorPct}%`, background: 'oklch(0.7 0.11 188)', display: 'flex', alignItems: 'center', paddingLeft: 16, color: '#06342c', fontSize: 14, fontWeight: 800 }}>{authorLabel}</div>
        <div style={{ width: `${100 - authorPct}%`, background: '#dceee9', display: 'flex', alignItems: 'center', justifyContent: 'center', color: T.textMid, fontSize: 13, fontWeight: 700 }}>{platLabel}</div>
      </div>
    </div>
  );
}

function Step({ label, value, highlight }) {
  return (
    <div style={{ flex: highlight ? 1.1 : 1, background: highlight ? 'oklch(0.7 0.11 188)' : 'rgba(255,255,255,0.08)', borderRadius: 14, padding: 20 }}>
      <div style={{ fontSize: 12.5, color: highlight ? '#06342c' : T.inkSoft, fontWeight: highlight ? 600 : 400 }}>{label}</div>
      <div style={{ fontSize: highlight ? 26 : 24, fontWeight: 800, color: highlight ? '#06342c' : '#fff', marginTop: 6 }}>{value}</div>
    </div>
  );
}
const Op = ({ ch }) => <div style={{ display: 'flex', alignItems: 'center', color: '#6f9aa4', fontSize: 20 }}>{ch}</div>;

export function PricingPage() {
  return (
    <div style={{ padding: '54px 56px 64px' }}>
      <div style={{ textAlign: 'center', maxWidth: 680, margin: '0 auto 44px' }}>
        <div style={{ display: 'inline-block', padding: '6px 14px', background: '#e3f3ec', borderRadius: 999, fontSize: 12.5, fontWeight: 700, color: '#297961', marginBottom: 18 }}>작가에게 가장 많이 남기는 구조</div>
        <h1 style={{ margin: '0 0 14px', fontSize: 36, fontWeight: 800, color: T.ink, letterSpacing: '-0.03em', lineHeight: 1.25 }}>월 요금 없이, 팔린 만큼<br />투명하게 나눕니다</h1>
        <p style={{ margin: 0, fontSize: 16, lineHeight: 1.75, color: T.muted }}>
          가입도, 글쓰기 에디터도, 출판도 무료예요. 작가에게 월 구독료를 받지 않습니다. 책이 팔릴 때만, 처음부터 공개된 비율로 정산합니다.
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16, maxWidth: 920, margin: '0 auto 44px' }}>
        <Stat value="0원" label="가입·에디터·출판 비용" />
        <Stat value="70%" label="한줄 직판 시 작가 몫" color="oklch(0.6 0.1 195)" />
        <Stat value="M+2" label="판매월 + 2개월 정산" />
      </div>

      <div style={{ maxWidth: 920, margin: '0 auto' }}>
        <h2 style={{ margin: '0 0 18px', fontSize: 20, fontWeight: 800, color: T.textStrong, letterSpacing: '-0.02em' }}>판매 채널별 분배율</h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 18, marginBottom: 44 }}>
          <ChannelCard title="SELF · 한줄 직판" desc="한줄 서점에서 직접 팔릴 때. 가장 높은 작가 몫." authorPct={70} authorLabel="작가 70%" platLabel="한줄 30%" recommend />
          <ChannelCard title="EXTERNAL · 외부 서점" desc="교보·예스24 등 외부 채널 판매 (서점 몫 포함)." authorPct={60} authorLabel="작가 60%" platLabel="서점·플랫폼 40%" />
        </div>

        <h2 style={{ margin: '0 0 18px', fontSize: 20, fontWeight: 800, color: T.textStrong, letterSpacing: '-0.02em' }}>정산은 이렇게 계산돼요</h2>
        <div style={{ background: T.ink, borderRadius: 22, padding: '34px 36px', marginBottom: 20 }}>
          <div style={{ fontSize: 13, color: T.inkSoft, marginBottom: 22 }}>예시 · 10,000원 책이 <b style={{ color: '#fff' }}>한줄 직판(SELF)</b>으로 1권 팔렸을 때</div>
          <div style={{ display: 'flex', alignItems: 'stretch', gap: 14, flexWrap: 'wrap' }}>
            <Step label="판매가" value="10,000원" />
            <Op ch="→" />
            <Step label="작가 몫 (70%)" value="7,000원" />
            <Op ch="−" />
            <Step label="원천징수 (3.3%)" value="231원" />
            <Op ch="=" />
            <Step label="실지급액" value="6,769원" highlight />
          </div>
        </div>
        <div style={{ display: 'flex', gap: 24, fontSize: 13, color: T.muted, lineHeight: 1.7, flexWrap: 'wrap' }}>
          <div style={{ flex: 1, minWidth: 260 }}><b style={{ color: T.textMid }}>원천징수란?</b> 개인 작가는 작가 몫에서 소득세 3% + 주민세 0.3% = 3.3%를 떼고 지급해요. (사업자 작가는 세금계산서 발행, 원천징수 없음)</div>
          <div style={{ flex: 1, minWidth: 260 }}><b style={{ color: T.textMid }}>정산 주기</b> 판매가 일어난 달 기준 2개월 뒤(M+2)에 등록한 계좌로 지급됩니다. 스튜디오에서 실시간 적립·예정 정산액을 확인할 수 있어요.</div>
        </div>
      </div>
    </div>
  );
}
