import { T } from './theme';

/**
 * 버튼 — 한줄 기본 액션 컴포넌트.
 * @param {'primary'|'secondary'|'ghost'|'danger'} [kind='primary']
 *   primary=딥틸 채움(주 액션) · secondary=테두리 · ghost=투명 · danger=삭제/경고
 * @param {'md'|'sm'} [size='md']
 * @param {boolean} [block] 전체 너비
 */
export function Button({ kind = 'primary', size = 'md', block, style, children, ...rest }) {
  const palette = {
    primary: { bg: T.ink, fg: T.inkText, bd: T.ink },
    secondary: { bg: T.surface, fg: T.textMid, bd: '#d6e4de' },
    ghost: { bg: 'transparent', fg: T.textMid, bd: 'transparent' },
    danger: { bg: '#fdeeea', fg: '#e0654f', bd: '#f3d3cb' },
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
