import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { PricingPage } from './PricingPage';

describe('PricingPage', () => {
  it('핵심 수치와 채널별 분배율을 보여준다', () => {
    render(<PricingPage />);
    expect(screen.getByText('0원')).toBeInTheDocument();
    expect(screen.getByText('70%')).toBeInTheDocument();
    expect(screen.getByText('SELF · 한줄 직판')).toBeInTheDocument();
    expect(screen.getByText('작가 70%')).toBeInTheDocument();
    expect(screen.getByText('EXTERNAL · 외부 서점')).toBeInTheDocument();
    expect(screen.getByText('작가 60%')).toBeInTheDocument();
  });

  it('정산 예시 계산이 원천징수 3.3%를 반영한다', () => {
    render(<PricingPage />);
    expect(screen.getByText('7,000원')).toBeInTheDocument();
    expect(screen.getByText('231원')).toBeInTheDocument();
    expect(screen.getByText('6,769원')).toBeInTheDocument();
  });
});
