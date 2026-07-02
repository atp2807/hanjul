import { T } from './theme';

/**
 * 입력 필드 — 라벨 + input. textarea는 as="textarea".
 * @param {string} [label]
 * @param {'input'|'textarea'} [as='input']
 */
export function Field({ label, as = 'input', style, ...rest }) {
  const Tag = as;
  return (
    <label style={{ display: 'block' }}>
      {label && (
        <span style={{ display: 'block', fontSize: 13, color: T.textSoft, marginBottom: 6 }}>
          {label}
        </span>
      )}
      <Tag
        style={{
          width: '100%',
          boxSizing: 'border-box',
          font: T.font,
          fontSize: 14,
          padding: '11px 13px',
          borderRadius: T.radius.md,
          border: `1px solid ${T.border}`,
          background: T.surface,
          color: T.textStrong,
          ...style,
        }}
        {...rest}
      />
    </label>
  );
}
