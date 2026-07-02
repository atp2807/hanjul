// 공용 컴포넌트는 @hanjul/ui 로 이전. Icon은 운영자 아이콘셋이라 앱에 유지.
export { Button, Card, Badge, Chip, Field, PageHeader } from '@hanjul/ui';

// ── 운영자 커스텀 SVG 아이콘 (고객 앱과 다른 셋) ──────
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
  reports: <path d="M5 21V4M5 4h12l-2 4 2 4H5" />,
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
