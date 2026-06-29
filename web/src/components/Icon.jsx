// 한줄 UI 아이콘 세트 — 디자인(한줄 아이콘.dc.html) 확장 아이콘. 24px 그리드 · 둥근 끝 라인.
// 이모지 대신 일관된 라인 아이콘으로. <Icon name="search" size={20} stroke="#0e4a5c" />
const PATHS = {
  search: <><circle cx="11" cy="11" r="6" /><path d="m20 20-4.3-4.3" /></>,
  bell: <><path d="M6 9a6 6 0 0 1 12 0c0 5 2 6 2 6H4s2-1 2-6Z" /><path d="M10 19a2 2 0 0 0 4 0" /></>,
  bookmark: <path d="M7 4h10v16l-5-3.5L7 20Z" />,
  heart: <path d="M12 20S4 15 4 9.5A3.5 3.5 0 0 1 12 7a3.5 3.5 0 0 1 8 2.5C20 15 12 20 12 20Z" />,
  star: <path d="m12 4 2.3 4.9 5.2.7-3.8 3.7.9 5.3L12 16.9 7.4 19.3l.9-5.3L4.5 10.3l5.2-.7z" />,
  share: <><circle cx="6" cy="12" r="2.4" /><circle cx="18" cy="6" r="2.4" /><circle cx="18" cy="18" r="2.4" /><path d="m8.1 10.9 7.8-3.7M8.1 13.1l7.8 3.7" /></>,
  settings: <><circle cx="12" cy="12" r="3" /><path d="M12 3v2.5M12 18.5V21M3 12h2.5M18.5 12H21M5.6 5.6l1.8 1.8M16.6 16.6l1.8 1.8M18.4 5.6l-1.8 1.8M7.4 16.6l-1.8 1.8" /></>,
  edit: <><path d="M14.5 5 19 9.5 8.5 20 4 20l0-4.5z" /><path d="m12.5 7 4.5 4.5" /></>,
  read: <><path d="M12 6C9 4 5.5 4 3.5 5v13c2-1 5.5-1 8.5 1 3-2 6.5-2 8.5-1V5c-2-1-5.5-1-8.5 1Z" /><path d="M12 6v13" /></>,
  download: <path d="M12 4v10M8 10.5l4 4 4-4M5 19h14" />,
  play: <path d="M7 18V6.5a.5.5 0 0 1 .77-.42l9 5.5a.5.5 0 0 1 0 .84l-9 5.5A.5.5 0 0 1 7 17.5Z" />,
  menu: <path d="M4 6h16M4 12h16M4 18h10" />,
  filter: <path d="M4 7h16M4 12h13M4 17h16" />,
  clock: <><circle cx="12" cy="12" r="8.5" /><path d="M12 7v5l3.5 2" /></>,
  check: <path d="M20 6 9 17l-5-5" />,
  chevron: <path d="M9 6 15 12 9 18" />,
  gift: <><rect x="4" y="9" width="16" height="11" rx="1.2" /><path d="M4 13h16M12 9v11" /><path d="M12 9c-3.5 0-4.5-5 0-3 4.5-2 3.5 3 0 3Z" /></>,
  ban: <><circle cx="12" cy="12" r="8.5" /><path d="m6.2 6.2 11.6 11.6" /></>,
};

export function Icon({ name, size = 22, stroke = 'currentColor', strokeWidth = 1.9, fill = 'none', style }) {
  const path = PATHS[name];
  if (!path) return null;
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} fill={fill} stroke={stroke} strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round" style={style} aria-hidden="true">
      {path}
    </svg>
  );
}
