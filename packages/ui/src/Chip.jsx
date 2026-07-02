import { T } from './theme';

/**
 * 필터 칩 — 목록 상단 카테고리/상태 필터. active면 딥틸 채움.
 * @param {object} props
 * @param {boolean} [props.active] 선택 상태
 * @param {import('react').CSSProperties} [props.style]
 * @param {import('react').ReactNode} [props.children]
 */
export function Chip({ active, style, children, ...rest }) {
  return (
    <button
      style={{
        font: T.font,
        fontSize: 13,
        fontWeight: 600,
        padding: '8px 16px',
        borderRadius: T.radius.pill,
        border: active ? `1px solid ${T.ink}` : `1px solid ${T.border}`,
        background: active ? T.ink : T.surface,
        color: active ? T.inkText : T.text,
        cursor: 'pointer',
        ...style,
      }}
      {...rest}
    >
      {children}
    </button>
  );
}
