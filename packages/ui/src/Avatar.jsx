import { avatarGradient, T } from './theme';

const SIZES = { xs: 24, sm: 32, md: 40, lg: 56, xl: 80 };
// 상태점은 흰 링(box-shadow) 위 장식 인디케이터라 텍스트 4.5:1 대상은 아니지만(비텍스트 3:1),
// 나머지 상태색이 전부 theme.js 토큰으로 통일된 데 맞춰 하드코딩 대신 토큰을 참조(2026-07-08).
const STATUS = { online: T.ok, away: T.warn, busy: T.danger, offline: T.faint };

// 이니셜 — 한글은 성 뺀 이름(끝 두 글자)이 더 개인적. 라틴은 두 단어 머리글자.
function initialsFor(name) {
  const n = (name || '').trim();
  if (!n) return '?';
  if (/[ㄱ-힝]/.test(n)) return n.length <= 2 ? n : n.slice(-2);
  const parts = n.split(/\s+/).filter(Boolean);
  return (parts.length > 1 ? parts[0][0] + parts[1][0] : n.slice(0, 2)).toUpperCase();
}

/**
 * 아바타 — 원형 유저 아바타. 이름 시드로 그라데이션을 결정론적으로 선택(같은 이름=같은 색,
 * 책 표지 coverGradient 와 동일 해시). src 있으면 이미지, 없으면 이니셜. status·ring 지원.
 * @param {object} props
 * @param {string} [props.name=''] 이니셜·그라데이션 시드
 * @param {string} [props.src] 있으면 이미지, 없으면 이니셜 원
 * @param {'xs'|'sm'|'md'|'lg'|'xl'|number} [props.size='md'] 토큰 프리셋 또는 px 숫자
 * @param {'online'|'away'|'busy'|'offline'} [props.status] 우하단 상태점
 * @param {boolean} [props.ring=false] 흰 테두리 — 색 배경·겹침 배치에서 분리감
 * @param {import('react').CSSProperties} [props.style]
 */
export function Avatar({ name = '', src, size = 'md', status, ring = false, style, ...rest }) {
  const px = typeof size === 'number' ? size : SIZES[size] ?? SIZES.md;
  const shadow = ring ? '0 0 0 2px #ffffff, 0 1px 3px rgba(12,58,50,0.18)' : 'none';
  const statusColor = STATUS[status];
  const dot = Math.max(8, Math.round(px * 0.28));
  return (
    <span
      title={name}
      style={{
        position: 'relative',
        display: 'inline-flex',
        width: px,
        height: px,
        flexShrink: 0,
        verticalAlign: 'middle',
        ...style,
      }}
      {...rest}
    >
      {src ? (
        <img
          src={src}
          alt={name}
          style={{ width: '100%', height: '100%', borderRadius: 999, objectFit: 'cover', display: 'block', boxShadow: shadow }}
        />
      ) : (
        <span
          style={{
            width: '100%',
            height: '100%',
            borderRadius: 999,
            background: avatarGradient(name),
            color: '#eafaf5',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontFamily: "'IBM Plex Sans KR', system-ui, sans-serif",
            fontWeight: 700,
            fontSize: Math.round(px * (px <= 28 ? 0.36 : 0.4)),
            letterSpacing: '-0.02em',
            lineHeight: 1,
            userSelect: 'none',
            boxShadow: shadow,
          }}
        >
          {initialsFor(name)}
        </span>
      )}
      {statusColor && (
        <span
          style={{
            position: 'absolute',
            right: 0,
            bottom: 0,
            width: dot,
            height: dot,
            borderRadius: 999,
            background: statusColor,
            boxShadow: '0 0 0 2px #ffffff',
          }}
        />
      )}
    </span>
  );
}
