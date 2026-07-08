import { T } from './theme';

/**
 * 버튼 — 한줄 기본 액션 컴포넌트.
 * @param {object} props
 * @param {'primary'|'secondary'|'ghost'|'danger'} [props.kind='primary'] primary=딥틸 채움(주 액션) · secondary=테두리 · ghost=투명 · danger=삭제/경고
 * @param {'md'|'sm'} [props.size='md']
 * @param {boolean} [props.block] 전체 너비
 * @param {import('react').CSSProperties} [props.style]
 * @param {import('react').ReactNode} [props.children]
 */
export function Button({ kind = 'primary', size = 'md', block, style, children, ...rest }) {
  const palette = {
    primary: { bg: T.ink, fg: T.inkText, bd: T.ink },
    secondary: { bg: T.surface, fg: T.textMid, bd: '#d6e4de' },
    ghost: { bg: 'transparent', fg: T.textMid, bd: 'transparent' },
    // danger fg는 theme.js 토큰 참조로 단일화(2026-07-08) — 이전엔 hex 복붙이라 T.danger의
    // WCAG 대비 조정(e0654f→c63c23)이 이 버튼엔 반영되지 않는 사각지대였음(Badge.jsx와 동일 문제).
    danger: { bg: T.dangerBg, fg: T.danger, bd: '#f3d3cb' },
  }[kind];
  const pad = size === 'sm' ? '8px 14px' : '13px 22px';
  const fs = size === 'sm' ? 13 : 15;
  return (
    <button
      style={{
        font: T.font,
        fontSize: fs,
        fontWeight: 700,
        padding: pad,
        borderRadius: T.radius.md,
        border: `1px solid ${palette.bd}`,
        background: palette.bg,
        color: palette.fg,
        cursor: 'pointer',
        width: block ? '100%' : undefined,
        whiteSpace: 'nowrap',
        ...style,
      }}
      {...rest}
    >
      {children}
    </button>
  );
}
