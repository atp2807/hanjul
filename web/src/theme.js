// 한줄 디자인 토큰 — 시안(한줄.dc.html) 기준 단일 소스.
// 민트/딥틸 팔레트 + IBM Plex Sans KR. 인라인 스타일에서 T.xxx 로 참조.
export const T = {
  bg: '#f3faf8', // 페이지 배경 (연민트)
  surface: '#ffffff',
  ink: '#0c3a32', // 브랜드 딥틸 — 로고·제목·주 버튼
  inkText: '#eafaf5', // ink 위 텍스트
  textStrong: '#16302a',
  text: '#2f5249',
  textMid: '#3f6258',
  textSoft: '#56716a',
  muted: '#7d908a',
  faint: '#9bb0a8',
  border: '#e3efea',
  borderSoft: '#eef2f0',
  tint: '#eef8f4', // 카드 hover/active
  accent: 'oklch(0.74 0.1 188)', // 로고 사각형·포인트 틸
  heroFrom: 'oklch(0.86 0.075 184)',
  heroTo: 'oklch(0.76 0.1 200)',
  radius: { sm: 8, md: 10, lg: 14, xl: 20, hero: 30, pill: 999 },
  font: "'IBM Plex Sans KR', -apple-system, BlinkMacSystemFont, system-ui, sans-serif",
  shadow: '0 24px 48px -20px rgba(12,58,50,0.22)',
};

// 표지 placeholder용 틸 그라데이션 (시안 카드 톤)
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
