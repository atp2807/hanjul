import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';

import { BUSINESS } from '../config/business';
import { Footer } from './Footer';

function renderFooter() {
  return render(
    <MemoryRouter>
      <Footer />
    </MemoryRouter>,
  );
}

describe('Footer', () => {
  it('사업자정보(상호·대표·사업자번호)를 표시한다', () => {
    renderFooter();
    // 상호는 상호줄·저작권줄 2곳에 노출됨
    expect(screen.getAllByText(new RegExp(BUSINESS.company)).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(new RegExp(`대표 ${BUSINESS.ceo}`))).toBeInTheDocument();
    expect(screen.getByText(new RegExp(BUSINESS.bizNo))).toBeInTheDocument();
  });

  it('필수 법률문서 링크를 건다 (실제 문서 제목)', () => {
    renderFooter();
    expect(screen.getByRole('link', { name: '서비스 이용약관' })).toHaveAttribute('href', '/legal/terms');
    expect(screen.getByRole('link', { name: '개인정보 처리방침' })).toHaveAttribute('href', '/legal/privacy');
    expect(screen.getByRole('link', { name: '청약철회·환불 정책' })).toHaveAttribute('href', '/legal/refund');
  });
});
