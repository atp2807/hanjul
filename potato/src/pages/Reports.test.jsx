import { fireEvent, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { renderWithProviders } from '@hanjul/test-utils';

vi.mock('../api', () => ({
  api: { reports: vi.fn(), resolveReport: vi.fn() },
}));

import { api } from '../api';
import Reports from './Reports';

const reports = [{ id: 'r1', targetType: 'BOOK', targetId: 'b-101', reason: '저작권 침해 의심' }];

beforeEach(() => {
  vi.clearAllMocks();
});

describe('Reports (운영자 신고 큐)', () => {
  it('신고 목록을 targetType 배지·ID·사유와 함께 보여준다', async () => {
    api.reports.mockResolvedValue(reports);
    renderWithProviders(<Reports />);
    expect(await screen.findByText('책 신고')).toBeInTheDocument();
    expect(screen.getByText('b-101')).toBeInTheDocument();
    expect(screen.getByText('저작권 침해 의심')).toBeInTheDocument();
    expect(screen.getByText('대기 1건')).toBeInTheDocument();
  });

  it('"조치 완료" 클릭 시 프롬프트 입력값으로 RESOLVE 조치하고 재조회한다', async () => {
    api.reports.mockResolvedValue(reports);
    api.resolveReport.mockResolvedValue({});
    vi.spyOn(window, 'prompt').mockReturnValue('경고 조치함');
    renderWithProviders(<Reports />);
    fireEvent.click(await screen.findByRole('button', { name: '조치 완료' }));
    await waitFor(() => expect(api.resolveReport).toHaveBeenCalledWith('r1', 'RESOLVE', '경고 조치함'));
    await waitFor(() => expect(api.reports.mock.calls.length).toBeGreaterThanOrEqual(2));
  });

  it('"기각" 클릭 시 사유 프롬프트 후 DISMISS로 조치한다', async () => {
    api.reports.mockResolvedValue(reports);
    api.resolveReport.mockResolvedValue({});
    const promptSpy = vi.spyOn(window, 'prompt').mockReturnValue('중복 신고');
    renderWithProviders(<Reports />);
    fireEvent.click(await screen.findByRole('button', { name: '기각' }));
    expect(promptSpy).toHaveBeenCalledWith('기각 사유 (선택)');
    await waitFor(() => expect(api.resolveReport).toHaveBeenCalledWith('r1', 'DISMISS', '중복 신고'));
  });

  it('프롬프트 취소(null) 시 resolveReport를 호출하지 않는다', async () => {
    api.reports.mockResolvedValue(reports);
    vi.spyOn(window, 'prompt').mockReturnValue(null);
    renderWithProviders(<Reports />);
    fireEvent.click(await screen.findByRole('button', { name: '조치 완료' }));
    expect(api.resolveReport).not.toHaveBeenCalled();
  });

  it('신고 목록 로드 실패 시 에러 메시지를 보여준다', async () => {
    api.reports.mockRejectedValue(new Error('boom'));
    renderWithProviders(<Reports />);
    expect(await screen.findByText('신고를 불러오지 못했습니다.')).toBeInTheDocument();
  });

  it('미처리 신고가 없으면 안내 문구를 보여준다', async () => {
    api.reports.mockResolvedValue([]);
    renderWithProviders(<Reports />);
    expect(await screen.findByText('미처리 신고가 없습니다.')).toBeInTheDocument();
    expect(screen.getByText('대기 0건')).toBeInTheDocument();
  });
});
