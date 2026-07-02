// 한줄 디자인 토큰 — web(고객) ∪ potato(운영자) 통합 단일 소스.
// 민트/딥틸 팔레트 + IBM Plex Sans KR. 인라인 스타일에서 T.xxx 로 참조.
// drift(따로 만들다 갈라진 미세차)는 web 값으로 통일, radius는 union.
export const T = {
  // ── 공통 팔레트 ──────────────────────────────────
  bg: '#f3faf8', // 페이지 배경 (연민트)
  surface: '#ffffff',
  ink: '#0e4a5c', // 브랜드 딥틸 — 로고·제목·주 버튼
  inkText: '#eafaf5', // ink 위 텍스트
  inkSoft: '#9bc6cf', // ink 카드 위 보조 텍스트
  accent: 'oklch(0.74 0.1 188)', // 로고 사각형·포인트 틸
  textStrong: '#143e4a',
  text: '#3f6b78',
  textMid: '#3f6b78',
  textSoft: '#52615b', // (통일: potato #52666e → web)
  muted: '#7d949c',
  faint: '#9bb0a8', // (통일: potato #9bb4bc → web)
  border: '#e3efea', // (통일: potato #e0ebe6 → web)
  borderSoft: '#eef2f0', // (통일: potato #eef4f1 → web)
  tint: '#eef8f4', // 카드 hover/active
  rowTint: '#f3faf8', // 리스트 row 배경 (운영 콘솔)
  // ── 히어로 그라데이션 (web 랜딩) ─────────────────
  heroFrom: 'oklch(0.86 0.075 184)',
  heroTo: 'oklch(0.76 0.1 200)',
  shadow: '0 24px 48px -20px rgba(12,58,50,0.22)',
  // ── 운영자 사이드바 (potato) ─────────────────────
  sidebar: '#072a33',
  sidebarText: '#8fb3ad',
  sidebarMuted: '#6f9aa4',
  // ── 상태 4색 (배지·버튼 톤) ──────────────────────
  okBg: '#e3f3ec',
  ok: '#2f8a6f',
  warnBg: '#fff3da',
  warn: '#c79318',
  dangerBg: '#fdeeea',
  danger: '#e0654f',
  infoBg: '#e8eeff',
  info: '#5b73c4',
  // ── 반경·폰트 (radius = web ∪ potato) ────────────
  radius: { sm: 8, md: 10, lg: 14, xl: 20, hero: 30, card: 18, pill: 999 },
  font: "'IBM Plex Sans KR', -apple-system, BlinkMacSystemFont, system-ui, sans-serif",
};

// 표지 placeholder 틸 그라데이션 (web 스토어 기준 — 고객이 보는 정본)
export const COVER_GRADIENTS = [
  'linear-gradient(160deg,#0c3a32,#1d6657)',
  'linear-gradient(160deg,oklch(0.72 0.1 195),oklch(0.62 0.11 215))',
  'linear-gradient(160deg,#e8f3ef,#cfe9e1)',
  'linear-gradient(160deg,oklch(0.78 0.09 178),oklch(0.68 0.11 192))',
  'linear-gradient(160deg,#163f37,#2a7a68)',
];

export function coverGradient(seed = '') {
  let h = 0;
  for (let i = 0; i < seed.length; i += 1) h = (h * 31 + seed.charCodeAt(i)) >>> 0;
  return COVER_GRADIENTS[h % COVER_GRADIENTS.length];
}
