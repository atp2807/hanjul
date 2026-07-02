import { T } from '../../theme';

/**
 * 배지 — 상태·라벨 pill.
 * @param {'mint'|'danger'|'warn'|'info'|'neutral'} [tone='mint']
 *   mint=성공/추천(초록) · danger=경고(빨강) · warn=주의(앰버) · info=정보(파랑) · neutral=중립
 */
export function Badge({ tone = 'mint', style, children, ...rest }) {
  const c = {
    mint: { bg: '#e3f3ec', fg: '#2f8a6f' },
    danger: { bg: '#fdeeea', fg: '#e0654f' },
    warn: { bg: '#fff3da', fg: '#c79318' },
    info: { bg: '#e8eeff', fg: '#5b73c4' },
    neutral: { bg: T.tint, fg: T.text },
  }[tone];
  return (
    <span
      style={{
        display: 'inline-block',
        background: c.bg,
        color: c.fg,
        fontSize: 12,
        fontWeight: 700,
        padding: '4px 11px',
        borderRadius: T.radius.pill,
        ...style,
      }}
      {...rest}
    >
      {children}
    </span>
  );
}
