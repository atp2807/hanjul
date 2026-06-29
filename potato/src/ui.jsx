import { T } from './theme';

export function Button({ kind = 'default', children, style, ...rest }) {
  const palette = {
    default: { bg: T.surface, fg: T.textStrong, bd: T.border },
    primary: { bg: T.ink, fg: T.inkText, bd: T.ink },
    danger: { bg: T.danger, fg: '#fff', bd: T.danger },
    ghost: { bg: 'transparent', fg: T.text, bd: T.border },
  }[kind];
  return (
    <button
      style={{
        font: T.font,
        fontSize: 14,
        fontWeight: 600,
        padding: '8px 14px',
        borderRadius: T.radius.md,
        border: `1px solid ${palette.bd}`,
        background: palette.bg,
        color: palette.fg,
        cursor: 'pointer',
        ...style,
      }}
      {...rest}
    >
      {children}
    </button>
  );
}

export function Card({ children, style }) {
  return (
    <div
      style={{
        background: T.surface,
        border: `1px solid ${T.border}`,
        borderRadius: T.radius.lg,
        padding: 20,
        ...style,
      }}
    >
      {children}
    </div>
  );
}

export function Badge({ tone = 'muted', children }) {
  const c = {
    muted: { bg: T.tint, fg: T.text },
    danger: { bg: '#fdecea', fg: T.danger },
    warn: { bg: '#fdf3e2', fg: T.warn },
    ok: { bg: '#e6f5ef', fg: T.ok },
  }[tone];
  return (
    <span
      style={{
        background: c.bg,
        color: c.fg,
        fontSize: 12,
        fontWeight: 600,
        padding: '3px 9px',
        borderRadius: T.radius.pill,
      }}
    >
      {children}
    </span>
  );
}

export function Field({ label, ...rest }) {
  return (
    <label style={{ display: 'block', marginBottom: 12 }}>
      <span style={{ display: 'block', fontSize: 13, color: T.textSoft, marginBottom: 6 }}>
        {label}
      </span>
      <input
        style={{
          width: '100%',
          font: T.font,
          fontSize: 14,
          padding: '10px 12px',
          borderRadius: T.radius.md,
          border: `1px solid ${T.border}`,
          background: T.surface,
          color: T.textStrong,
        }}
        {...rest}
      />
    </label>
  );
}
