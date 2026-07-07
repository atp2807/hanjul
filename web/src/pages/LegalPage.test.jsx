import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { renderWithProviders } from '@hanjul/test-utils';
import { LegalPage } from './LegalPage';

function renderAt(slug) {
  return renderWithProviders(<LegalPage />, { path: '/legal/:slug', at: `/legal/${slug}` });
}

describe('LegalPage', () => {
  it('유효한 문서를 제목·본문과 함께 렌더한다', () => {
    renderAt('privacy');
    expect(screen.getByRole('heading', { level: 1, name: '개인정보 처리방침' })).toBeInTheDocument();
    // 개인정보보호법 §30 필수항목이 본문에 들어있다
    expect(screen.getByRole('heading', { name: /개인정보 보호책임자/ })).toBeInTheDocument();
  });

  it('청약철회 문서에 전자책 제한 조항이 있다', () => {
    renderAt('refund');
    expect(screen.getByRole('heading', { name: /디지털콘텐츠.*청약철회의 제한/ })).toBeInTheDocument();
  });

  it('없는 슬러그는 안내 문구', () => {
    renderAt('nonexistent');
    expect(screen.getByText(/문서를 찾을 수 없습니다/)).toBeInTheDocument();
  });
});
