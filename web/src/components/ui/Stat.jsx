import { T } from '../../theme';

/**
 * 통계 카드 — 큰 숫자 + 라벨. 대시보드·수익 요약용.
 * @param {string} label
 * @param {string|number} value
 * @param {string} [color] 값 색상 (기본 딥틸)
 */
export function Stat({ label, value, color }) {
  return (
    <div style={{ background: T.surface, borderRadius: 18, padding: 26, textAlign: 'center' }}>
      <div style={{ fontSize: 34, fontWeight: 800, color: color || T.ink, letterSpacing: '-0.02em' }}>
        {value}
      </div>
      <div style={{ fontSize: 13.5, color: T.muted, marginTop: 6 }}>{label}</div>
    </div>
  );
}
