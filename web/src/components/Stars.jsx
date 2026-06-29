import { Icon } from './Icon';

// 평점 별 — 표시/입력 공용 (★ 이모지 대체, 중앙화).
// 표시: <Stars value={4.2} />   입력: <Stars value={rating} onRate={setRating} size={30} />
const GOLD = 'oklch(0.7 0.13 70)';
const EMPTY = '#dfe7e3';

export function Stars({ value = 0, max = 5, size = 16, onRate, gap = 2 }) {
  const filled = Math.round(value);
  return (
    <span style={{ display: 'inline-flex', gap, alignItems: 'center' }}>
      {Array.from({ length: max }, (_, i) => {
        const n = i + 1;
        const on = n <= filled;
        return (
          <span
            key={n}
            onClick={onRate ? () => onRate(n) : undefined}
            role={onRate ? 'button' : undefined}
            aria-label={onRate ? `별점 ${n}점` : undefined}
            style={{ display: 'inline-flex', cursor: onRate ? 'pointer' : 'default' }}
          >
            <Icon name="star" size={size} fill={on ? GOLD : 'none'} stroke={on ? GOLD : EMPTY} strokeWidth={1.6} />
          </span>
        );
      })}
    </span>
  );
}
