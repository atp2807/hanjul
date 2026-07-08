import { T } from './theme';

/**
 * 배지 — 상태·라벨 pill.
 * @param {object} props
 * @param {'mint'|'ok'|'danger'|'warn'|'info'|'neutral'} [props.tone='mint'] mint(=ok)=성공/추천(초록) · danger=경고(빨강) · warn=주의(앰버) · info=정보(파랑) · neutral=중립
 * @param {import('react').CSSProperties} [props.style]
 * @param {import('react').ReactNode} [props.children]
 */
export function Badge({ tone = 'mint', style, children, ...rest }) {
  // theme.js 토큰 참조로 단일화(2026-07-08) — 이전엔 hex를 여기 복붙해뒀던 탓에
  // theme.js의 WCAG 대비 조정이 배지에 반영되지 않는 사각지대였음.
  const c = {
    mint: { bg: T.okBg, fg: T.ok },
    ok: { bg: T.okBg, fg: T.ok }, // potato 별칭 (= mint)
    danger: { bg: T.dangerBg, fg: T.danger },
    warn: { bg: T.warnBg, fg: T.warn },
    info: { bg: T.infoBg, fg: T.info },
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
