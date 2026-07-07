import { screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { renderWithProviders } from '@hanjul/test-utils';

vi.mock('../api', () => ({
  api: { dashboard: vi.fn() },
}));

import { api } from '../api';
import Dashboard from './Dashboard';

const stats = { accounts: 128, booksTotal: 40, booksPublished: 31, booksBlocked: 2, reportsOpen: 5 };

// KPI 카드는 Card > [라벨div, 값div(값 텍스트노드 + suffix span)] 구조 — 라벨 텍스트로 카드를 찾아
// 그 형제(값) div 의 textContent(값+suffix 결합)를 그대로 비교한다.
function kpiCard(label) {
  return screen.getByText(label).parentElement;
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe('Dashboard (운영자 대시보드)', () => {
  it('통계 로드 성공 시 KPI 값과 단위를 보여준다', async () => {
    api.dashboard.mockResolvedValue(stats);
    renderWithProviders(<Dashboard />);
    await screen.findByText('가입 계정');
    expect(kpiCard('가입 계정').children[1].textContent).toBe('128명');
    expect(kpiCard('전체 책').children[1].textContent).toBe('40권');
    expect(kpiCard('출판중').children[1].textContent).toBe('31권');
    expect(kpiCard('차단(takedown)').children[1].textContent).toBe('2권');
  });

  it('값이 없으면(null) 폴백(–)을 보여주고 단위는 붙이지 않는다', async () => {
    api.dashboard.mockResolvedValue({
      accounts: null,
      booksTotal: null,
      booksPublished: null,
      booksBlocked: null,
    });
    renderWithProviders(<Dashboard />);
    await screen.findByText('가입 계정');
    expect(kpiCard('가입 계정').children[1].textContent).toBe('–');
    expect(kpiCard('전체 책').children[1].textContent).toBe('–');
    expect(kpiCard('출판중').children[1].textContent).toBe('–');
    expect(kpiCard('차단(takedown)').children[1].textContent).toBe('–');
  });

  it('로딩 중(응답 전)에는 폴백(–)을 보여준다', () => {
    api.dashboard.mockReturnValue(new Promise(() => {})); // 응답이 오지 않는 상태를 흉내
    renderWithProviders(<Dashboard />);
    expect(kpiCard('가입 계정').children[1].textContent).toBe('–');
  });

  it('통계 로드 실패 시 에러 메시지를 보여준다', async () => {
    api.dashboard.mockRejectedValue(new Error('boom'));
    renderWithProviders(<Dashboard />);
    expect(await screen.findByText('통계를 불러오지 못했습니다.')).toBeInTheDocument();
  });
});
