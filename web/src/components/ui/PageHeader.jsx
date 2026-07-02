import { T } from '../../theme';

/**
 * 페이지 헤더 — 제목 + 부제 + 우측 액션.
 * @param {string} title
 * @param {string} [subtitle]
 * @param {React.ReactNode} [right] 우측 액션 영역
 */
export function PageHeader({ title, subtitle, right }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 16, marginBottom: 22 }}>
      <div>
        <h1 style={{ margin: 0, fontSize: 26, fontWeight: 800, color: T.ink, letterSpacing: '-0.025em' }}>
          {title}
        </h1>
        {subtitle && <div style={{ fontSize: 14, color: T.muted, marginTop: 4 }}>{subtitle}</div>}
      </div>
      {right}
    </div>
  );
}
