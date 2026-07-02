import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import * as payoutsApi from '../services/api/payouts';
import { SettlementPage } from './SettlementPage';

let mockUser = { id: 'a1', email: 'me@x.com' };
vi.mock('../services/api/payouts');
vi.mock('../auth/AuthContext', () => ({ useAuth: () => ({ user: mockUser }) }));

function renderPage() {
  return render(
    <MemoryRouter>
      <SettlementPage />
    </MemoryRouter>,
  );
}

describe('SettlementPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUser = { id: 'a1', email: 'me@x.com' };
    payoutsApi.getBankAccount.mockResolvedValue({ id: 'b1', bank: '국민', accountNoMasked: '****7890', holderName: '나' });
    payoutsApi.getPayable.mockResolvedValue({ grossAmt: 7000, withholdingAmt: 231, netAmt: 6769, orderCount: 1 });
    payoutsApi.getPayouts.mockResolvedValue([]);
  });

  it('출금 가능액과 계좌를 보여준다', async () => {
    renderPage();
    expect(await screen.findByText('6,769원')).toBeInTheDocument();
    expect(screen.getByText(/\*\*\*\*7890/)).toBeInTheDocument();
  });

  it('출금 신청 버튼이 requestPayout을 호출한다', async () => {
    payoutsApi.requestPayout.mockResolvedValue({ id: 'p1' });
    renderPage();
    const btn = await screen.findByText('출금 신청');
    await waitFor(() => expect(btn).not.toBeDisabled());
    fireEvent.click(btn);
    await waitFor(() => expect(payoutsApi.requestPayout).toHaveBeenCalledTimes(1));
  });

  it('출금 가능액 0이면 신청 버튼 비활성', async () => {
    payoutsApi.getPayable.mockResolvedValue({ grossAmt: 0, withholdingAmt: 0, netAmt: 0, orderCount: 0 });
    renderPage();
    await waitFor(() => expect(screen.getByText('출금 신청')).toBeDisabled());
  });

  it('계좌 미등록이면 등록 폼을 보여준다', async () => {
    payoutsApi.getBankAccount.mockResolvedValue(null);
    renderPage();
    expect(await screen.findByPlaceholderText('홍길동')).toBeInTheDocument();
  });
});
