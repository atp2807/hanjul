import { Badge } from '@hanjul/ui';

// 연령 등급 라벨 — ALL은 배지를 아예 렌더하지 않아(대다수 도서가 ALL) 노이즈를 막는다.
const RATING_LABEL = {
  AGE12: '12세',
  AGE15: '15세',
  AGE18: '19세 이용가',
};

/**
 * 콘텐츠 연령 등급 배지 — 스토어 카드·상세 페이지에서 공용으로 사용.
 * AGE18은 danger 톤(유페이퍼 성인물 띠지 관례)으로 강조, 나머지는 중립 톤.
 * @param {object} props
 * @param {string} [props.rating] 'ALL' | 'AGE12' | 'AGE15' | 'AGE18' — 미지정/ALL이면 null 반환
 * @param {import('react').CSSProperties} [props.style]
 */
export function RatingBadge({ rating, style }) {
  if (!rating || rating === 'ALL') return null;
  const label = RATING_LABEL[rating] || rating;
  const tone = rating === 'AGE18' ? 'danger' : 'neutral';
  return (
    <Badge tone={tone} style={style}>
      {label}
    </Badge>
  );
}
