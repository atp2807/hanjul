import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('../api', () => ({
  api: {
    payouts: vi.fn(),
    approvePayout: vi.fn(),
    rejectPayout: vi.fn(),
    payPayout: vi.fn(),
  },
}));

import { api } from '../api';
import Payouts from './Payouts';

const requested = [
  {
    id: 'p1', netAmt: 96700, withholdingAmt: 3300, statusCd: 'REQUESTED',
    bankCd: '국민', accountNoMasked: '****1234', holderName: '김작가',
  },
];

beforeEach(() => {
  vi.clearAllMocks();
  api.payouts.mockResolvedValue(requested);
  api.approvePayout.mockResolvedValue({});
  api.rejectPayout.mockResolvedValue({});
  api.payPayout.mockResolvedValue({});
});

describe('Payouts (운영자 출금관리)', () => {
  it('신청된 출금을 실지급액·원천징수와 함께 보여준다', async () => {
    render(<Payouts />);
    expect(await screen.findByText('96,700원')).toBeInTheDocument();
    expect(screen.getByText(/원천징수 3,300원/)).toBeInTheDocument();
  });

  it('승인 버튼이 approvePayout 호출 후 목록을 다시 불러온다', async () => {
    render(<Payouts />);
    fireEvent.click(await screen.findByRole('button', { name: '승인' }));
    await waitFor(() => expect(api.approvePayout).toHaveBeenCalledWith('p1'));
    await waitFor(() => expect(api.payouts.mock.calls.length).toBeGreaterThanOrEqual(2));
  });

  it('반려는 사유 프롬프트를 받아 rejectPayout을 호출한다', async () => {
    vi.spyOn(window, 'prompt').mockReturnValue('증빙 부족');
    render(<Payouts />);
    fireEvent.click(await screen.findByRole('button', { name: '반려' }));
    await waitFor(() => expect(api.rejectPayout).toHaveBeenCalledWith('p1', '증빙 부족'));
  });

  it('탭 전환 시 해당 상태로 다시 조회한다', async () => {
    render(<Payouts />);
    await screen.findByText('96,700원');
    fireEvent.click(screen.getByText('지급완료')); // PAID 탭 Chip
    await waitFor(() => expect(api.payouts).toHaveBeenCalledWith('PAID'));
  });

  it('빈 목록이면 안내를 보여준다', async () => {
    api.payouts.mockResolvedValue([]);
    render(<Payouts />);
    expect(await screen.findByText('해당 상태의 출금이 없습니다.')).toBeInTheDocument();
  });
});
