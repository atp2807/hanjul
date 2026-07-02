import { T } from './theme';

/**
 * 카드 — 콘텐츠 컨테이너. 흰 배경 + 라운드(18).
 * @param {boolean} [bordered] 테두리 추가 (기본은 그림자만)
 * @param {'ink'} [tone] ink=딥틸 배경(강조 카드, 텍스트는 밝게)
 */
export function Card({ bordered, tone, style, children, ...rest }) {
  const isInk = tone === 'ink';
  return (
    <div
      style={{
        background: isInk ? T.ink : T.surface,
        borderRadius: 18,
        padding: 24,
        border: bordered ? `1px solid ${T.borderSoft}` : 'none',
        boxShadow: bordered ? 'none' : '0 1px 3px rgba(12,58,50,0.06)',
        color: isInk ? T.inkText : undefined,
        ...style,
      }}
      {...rest}
    >
      {children}
    </div>
  );
}
