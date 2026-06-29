// 하단 탭 아이콘 — 디자인(한줄 아이콘.dc.html) 라인(비활성)/채움(활성).
// 24px 그리드 · 둥근 끝. studio(펜)만 라인 단독.
const INK = '#0e4a5c';
const MUTED = '#9bb4bc';

function Svg({ children, fill = 'none', stroke, sw = 1.9 }) {
  return (
    <svg viewBox="0 0 24 24" width="26" height="26" fill={fill} stroke={stroke} strokeWidth={sw} strokeLinecap="round" strokeLinejoin="round">
      {children}
    </svg>
  );
}

const LINE = {
  home: <><path d="M4 11.5 12 4l8 7.5" /><path d="M6 10.5V20h12v-9.5" /><path d="M10 20v-5h4v5" /></>,
  reviewers: <><rect x="4" y="9" width="16" height="11" rx="1.2" /><path d="M4 13h16M12 9v11" /><path d="M12 9c-3.5 0-4.5-5 0-3 4.5-2 3.5 3 0 3Z" /></>,
  library: <><rect x="4.5" y="4" width="3.5" height="16" rx="0.8" /><rect x="9.5" y="4" width="3.5" height="16" rx="0.8" /><path d="m15.2 5.2 3.2.7-2.6 14.4-3.2-.7z" /></>,
  studio: <><path d="M14.5 5 19 9.5 8.5 20 4 20l0-4.5z" /><path d="m12.5 7 4.5 4.5" /></>,
  my: <><circle cx="12" cy="8" r="3.6" /><path d="M5.5 20a6.5 6.5 0 0 1 13 0" /></>,
};

const FILLED = {
  home: <path d="M3.6 11.4 12 3.6l8.4 7.8a.6.6 0 0 1-.4 1.05H19V20a1 1 0 0 1-1 1h-3.5v-5h-5v5H6a1 1 0 0 1-1-1v-7.55H4a.6.6 0 0 1-.4-1.05Z" />,
  reviewers: <><path d="M12 9c-3.5 0-4.5-5 0-3 4.5-2 3.5 3 0 3Z" /><rect x="4" y="9" width="7" height="4" rx="0.8" /><rect x="13" y="9" width="7" height="4" rx="0.8" /><path d="M4.6 13H11v8H6a1 1 0 0 1-1-1v-6.4ZM13 13h6.4v6.6a1 1 0 0 1-1 1H13Z" /></>,
  library: <><rect x="4.5" y="4" width="3.5" height="16" rx="0.8" /><rect x="9.5" y="4" width="3.5" height="16" rx="0.8" /><path d="m15.2 5.2 3.2.7-2.6 14.4-3.2-.7z" /></>,
  my: <><circle cx="12" cy="8" r="3.6" /><path d="M5.5 20a6.5 6.5 0 0 1 13 0Z" /></>,
};

export function TabIcon({ name, active }) {
  // studio는 채움 변형이 없어 라인+색으로
  if (active && FILLED[name]) {
    return <Svg fill={INK} stroke={INK} sw={1.2}>{FILLED[name]}</Svg>;
  }
  return <Svg stroke={active ? INK : MUTED}>{LINE[name] || LINE.home}</Svg>;
}
