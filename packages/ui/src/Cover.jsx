import { coverGradient, T } from './theme';

/**
 * 책 표지 — url 있으면 이미지, 없으면 제목 시드 그라데이션 placeholder. 세로 3:4.3.
 * 실표지(업로드/생성)가 들어오면 이 컴포넌트 한 곳에서 이미지로 바뀌는 seam.
 * @param {object} props
 * @param {string} [props.url] 표지 이미지 URL — 있으면 이미지 표시
 * @param {string} [props.title=''] 제목 — 그라데이션 시드 + (label=true일 때) placeholder 텍스트.
 *   UUID 등 사람이 못 읽는 값을 시드로 써야 할 때는 title은 그대로 두고 alt로 실제 제목을 따로 넘길 것
 *   (lr-ca34f579 ③ — potato Moderation이 title={book.id}를 alt로도 흘려보내던 문제).
 * @param {string} [props.alt] 스크린리더용 대체 텍스트 override. 생략 시 title을 그대로 씀(기존 동작 유지).
 *   명시적으로 ''(빈 문자열)을 넘기면 장식용으로 간주해 aria-hidden 처리.
 * @param {number} [props.width] px 고정폭 (미지정 시 100%, 컨테이너 채움)
 * @param {number|string} [props.radius] 모서리 반경 (기본 T.radius.lg)
 * @param {boolean} [props.label=true] placeholder에 제목 텍스트 표시 (작은 썸네일은 false)
 * @param {number} [props.labelSize=14] placeholder 제목 글자 크기
 * @param {import('react').CSSProperties} [props.style] 추가 스타일 (boxShadow·opacity 등)
 */
export function Cover({ url, title = '', alt, width, radius = T.radius.lg, label = true, labelSize = 14, style, ...rest }) {
  const altText = alt ?? title;
  const decorative = altText === '';
  const base = {
    width: width ?? '100%',
    aspectRatio: '3 / 4.3',
    borderRadius: radius,
    boxSizing: 'border-box',
    ...(width ? { flexShrink: 0 } : null),
    ...style,
  };
  if (url) {
    return <img src={url} alt={altText} loading="lazy" style={{ ...base, objectFit: 'cover', display: 'block' }} {...rest} />;
  }
  // label=true면 title이 눈에 보이는 텍스트로 그대로 렌더돼 그 자체가 접근성 이름이 됨 — 별도 ARIA 불필요.
  // label=false(작은 썸네일 등)일 때만 시각 텍스트가 없으므로 role/aria-label(또는 장식이면 aria-hidden)로 보완.
  const a11yProps = label
    ? null
    : decorative
      ? { 'aria-hidden': true }
      : { role: 'img', 'aria-label': altText };
  return (
    <div
      {...a11yProps}
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
