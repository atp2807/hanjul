import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { RatingBadge } from './RatingBadge';

describe('RatingBadge', () => {
  it('ALL이면 아무것도 렌더하지 않는다', () => {
    const { container } = render(<RatingBadge rating="ALL" />);
    expect(container).toBeEmptyDOMElement();
  });

  it('rating 미지정이면 아무것도 렌더하지 않는다', () => {
    const { container } = render(<RatingBadge />);
    expect(container).toBeEmptyDOMElement();
  });

  it('AGE12는 "12세"를 보여준다', () => {
    render(<RatingBadge rating="AGE12" />);
    expect(screen.getByText('12세')).toBeInTheDocument();
  });

  it('AGE15는 "15세"를 보여준다', () => {
    render(<RatingBadge rating="AGE15" />);
    expect(screen.getByText('15세')).toBeInTheDocument();
  });

  it('AGE18은 "19세 이용가"를 빨강 강조로 보여준다', () => {
    render(<RatingBadge rating="AGE18" />);
    const badge = screen.getByText('19세 이용가');
    expect(badge).toBeInTheDocument();
    // danger 톤(Badge tone="danger")은 T.danger 전경색을 쓴다 — 하드코딩 회피 확인용 스모크.
    expect(badge).toHaveStyle({ color: 'rgb(198, 60, 35)' });
  });
});
