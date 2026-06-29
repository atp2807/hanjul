// 운영자 콘솔 디자인 토큰 — 「한줄 운영자.dc.html」 시안 기준.
// 고객 앱(web)과 같은 민트/딥틸 팔레트, 단 사이드바는 더 진한 #072a33.
export const T = {
  bg: '#f3faf8',
  surface: '#ffffff',
  ink: '#0e4a5c', // 브랜드 딥틸 — 제목·primary 버튼
  inkText: '#eafaf5',
  sidebar: '#072a33', // 운영 사이드바(고객앱보다 진함)
  sidebarText: '#8fb3ad', // 비활성 nav
  sidebarMuted: '#6f9aa4',
  accent: 'oklch(0.74 0.1 188)', // 로고 사각형·포인트 틸
  textStrong: '#143e4a',
  text: '#3f6b78',
  textSoft: '#52666e',
  muted: '#7d949c',
  faint: '#9bb4bc',
  border: '#e0ebe6',
  borderSoft: '#eef4f1',
  rowTint: '#f3faf8',
  // 상태 4색 (배지·버튼 톤)
  okBg: '#e3f3ec',
  ok: '#2f8a6f',
  warnBg: '#fff3da',
  warn: '#c79318',
  dangerBg: '#fdeeea',
  danger: '#e0654f',
  infoBg: '#e8eeff',
  info: '#5b73c4',
  radius: { sm: 10, md: 11, lg: 13, card: 18, pill: 999 },
  font: "'IBM Plex Sans KR', -apple-system, BlinkMacSystemFont, system-ui, sans-serif",
};

const COVER_GRADIENTS = [
  'linear-gradient(160deg,#16525e,#2aa0a8)',
  'linear-gradient(160deg,oklch(0.7 0.11 205),oklch(0.6 0.12 228))',
  'linear-gradient(160deg,oklch(0.78 0.09 176),oklch(0.68 0.11 190))',
  'linear-gradient(160deg,#1d7e8e,#3fb0b0)',
  'linear-gradient(160deg,oklch(0.72 0.1 200),oklch(0.62 0.11 222))',
];

export function coverGradient(seed = '') {
  let h = 0;
  for (let i = 0; i < seed.length; i += 1) h = (h * 31 + seed.charCodeAt(i)) >>> 0;
  return COVER_GRADIENTS[h % COVER_GRADIENTS.length];
}
