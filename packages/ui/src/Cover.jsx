import { coverGradient, T } from './theme';

/**
 * 책 표지 — url 있으면 이미지, 없으면 제목 시드 그라데이션 placeholder. 세로 3:4.3.
 * 실표지(업로드/생성)가 들어오면 이 컴포넌트 한 곳에서 이미지로 바뀌는 seam.
 * @param {object} props
 * @param {string} [props.url] 표지 이미지 URL — 있으면 이미지 표시
 * @param {string} [props.title=''] 제목 — 그라데이션 시드 + placeholder 텍스트
 * @param {number} [props.width] px 고정폭 (미지정 시 100%, 컨테이너 채움)
 * @param {number|string} [props.radius] 모서리 반경 (기본 T.radius.lg)
 * @param {boolean} [props.label=true] placeholder에 제목 텍스트 표시 (작은 썸네일은 false)
 * @param {number} [props.labelSize=14] placeholder 제목 글자 크기
 * @param {import('react').CSSProperties} [props.style] 추가 스타일 (boxShadow·opacity 등)
 */
export function Cover({ url, title = '', width, radius = T.radius.lg, label = true, labelSize = 14, style, ...rest }) {
  const base = {
    width: width ?? '100%',
    aspectRatio: '3 / 4.3',
    borderRadius: radius,
    boxSizing: 'border-box',
    ...(width ? { flexShrink: 0 } : null),
    ...style,
  };
  if (url) {
    return <img src={url} alt={title} loading="lazy" style={{ ...base, objectFit: 'cover', display: 'block' }} {...rest} />;
  }
  return (
    <div
      style={{
        ...base,
        background: coverGradient(title),
        display: 'flex',
        alignItems: 'flex-end',
        padding: label ? 14 : 0,
        color: '#dff5ef',
        fontSize: labelSize,
        fontWeight: 700,
        lineHeight: 1.3,
      }}
      {...rest}
    >
      {label ? title : null}
    </div>
  );
}
