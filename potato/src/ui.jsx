import { T } from './theme';

// ── 커스텀 SVG 아이콘 (이모지 대체) ──────────────────
const ICONS = {
  dashboard: (
    <>
      <rect x="3" y="3" width="7" height="9" rx="1.5" />
      <rect x="14" y="3" width="7" height="5" rx="1.5" />
      <rect x="14" y="12" width="7" height="9" rx="1.5" />
      <rect x="3" y="16" width="7" height="5" rx="1.5" />
    </>
  ),
  moderation: <path d="M12 3l7 3v5c0 4.5-3 7.5-7 9-4-1.5-7-4.5-7-9V6l7-3z" />,
  reports: (
    <>
      <path d="M5 21V4M5 4h12l-2 4 2 4H5" />
    </>
  ),
  accounts: (
    <>
      <circle cx="9" cy="8" r="3.2" />
      <path d="M3.5 20a5.5 5.5 0 0 1 11 0" />
      <path d="M16 5.2a3 3 0 0 1 0 5.6M17.5 20a5.5 5.5 0 0 0-3-4.9" />
    </>
  ),
  book: <path d="M5 4h11a2 2 0 0 1 2 2v14H7a2 2 0 0 1-2-2V4zM5 17h13" />,
  logout: (
    <>
      <path d="M14 21H6a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h8" />
      <path d="M17 8l4 4-4 4M21 12H9" />
    </>
  ),
  search: (
    <>
      <circle cx="11" cy="11" r="7" />
      <path d="M21 21l-4.3-4.3" />
    </>
  ),
  payout: (
    <>
      <rect x="3" y="6" width="18" height="12" rx="2" />
      <circle cx="12" cy="12" r="2.5" />
      <path d="M6 9v6M18 9v6" />
    </>
  ),
};

export function Icon({ name, size = 18, color = 'currentColor', style }) {
  return (
    <svg
      viewBox="0 0 24 24"
      width={size}
      height={size}
      fill="none"
      stroke={color}
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      style={style}
    >
      {ICONS[name]}
    </svg>
  );
}

// ── 버튼 ──────────────────────────────────────────────
export function Button({ kind = 'secondary', children, style, ...rest }) {
  const p = {
    primary: { bg: T.ink, fg: T.inkText, bd: T.ink, w: 700 },
    secondary: { bg: T.surface, fg: T.text, bd: '#d6e4de', w: 600 },
    danger: { bg: T.dangerBg, fg: T.danger, bd: T.dangerBg, w: 700 },
    dangerSolid: { bg: T.danger, fg: '#fff', bd: T.danger, w: 700 },
  }[kind];
  return (
    <button
      style={{
        font: T.font,
        fontSize: 13.5,
        fontWeight: p.w,
        padding: '10px 18px',
        borderRadius: T.radius.md,
        border: `1px solid ${p.bd}`,
        background: p.bg,
        color: p.fg,
        cursor: 'pointer',
        whiteSpace: 'nowrap',
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
        borderRadius: T.radius.card,
        padding: 22,
        border: `1px solid ${T.borderSoft}`,
        ...style,
      }}
    >
      {children}
    </div>
  );
}

// 상태 배지 — tone: ok | warn | danger | info | neutral
export function Badge({ tone = 'neutral', children, style }) {
  const c = {
    ok: { bg: T.okBg, fg: T.ok },
    warn: { bg: T.warnBg, fg: T.warn },
    danger: { bg: T.dangerBg, fg: T.danger },
    info: { bg: T.infoBg, fg: T.info },
    neutral: { bg: '#eef6f3', fg: T.text },
  }[tone];
  return (
    <span
      style={{
        display: 'inline-block',
        background: c.bg,
        color: c.fg,
        fontSize: 11.5,
        fontWeight: 700,
        padding: '3px 10px',
        borderRadius: T.radius.pill,
        ...style,
      }}
    >
      {children}
    </span>
  );
}

// 필터 칩 (active=딥틸 채움)
export function Chip({ active, children, ...rest }) {
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
      }}
      {...rest}
    >
      {children}
    </button>
  );
}

export function Field({ label, style, ...rest }) {
  return (
    <label style={{ display: 'block' }}>
      {label && (
        <span style={{ display: 'block', fontSize: 13, color: T.textSoft, marginBottom: 6 }}>
          {label}
        </span>
      )}
      <input
        style={{
          width: '100%',
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

export function PageHeader({ title, subtitle, right }) {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: 22,
        gap: 16,
      }}
    >
      <div>
        <h1
          style={{
            margin: 0,
            fontSize: 24,
            fontWeight: 800,
            color: T.ink,
            letterSpacing: '-0.025em',
          }}
        >
          {title}
        </h1>
        {subtitle && (
          <div style={{ fontSize: 14, color: T.muted, marginTop: 4 }}>{subtitle}</div>
        )}
      </div>
      {right}
    </div>
  );
}
