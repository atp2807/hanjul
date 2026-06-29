// 한줄 브랜드 마크 — "강조된 한 줄"(옅은 줄 사이 굵은 한 줄). 딥틸 스쿼클.
// 디자인: 한줄 아이콘.dc.html 컨셉 A. 26~96px 권장.
export function BrandMark({ size = 26, rounded = 0.225, glyph = '#fff' }) {
  return (
    <span
      aria-hidden="true"
      style={{
        width: size, height: size, flexShrink: 0,
        borderRadius: `${rounded * 100}%`,
        background: 'linear-gradient(160deg,#0e4a5c,#1d7e8e)',
        display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
      }}
    >
      <svg viewBox="0 0 100 100" width="62%" height="62%" style={{ display: 'block' }}>
        <rect x="22" y="19" width="26" height="8" rx="4" fill={glyph} opacity="0.42" />
        <rect x="22" y="39" width="56" height="10" rx="5" fill={glyph} transform="rotate(-5 50 44)" />
        <circle cx="50" cy="71" r="7" fill={glyph} opacity="0.42" />
      </svg>
    </span>
  );
}
