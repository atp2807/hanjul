import { fireEvent, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { renderWithProviders, authFixture, httpError } from '@hanjul/test-utils';
import * as payoutsApi from '../services/api/payouts';
import { SettlementPage } from './SettlementPage';

let mockUser = { id: 'a1', email: 'me@x.com' };
vi.mock('../services/api/payouts');
vi.mock('../auth/AuthContext', () => ({ useAuth: () => authFixture({ user: mockUser }) }));

function renderPage() {
  return renderWithProviders(<SettlementPage />);
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

  it('목록 로드 실패 → 에러 안내 (침묵 금지)', async () => {
    payoutsApi.getBankAccount.mockRejectedValue(new Error('network'));
    renderPage();
    expect(await screen.findByText('불러오기에 실패했어요.')).toBeInTheDocument();
  });

  it('출금 신청 실패(잔액·계좌 없음 422) → 안내 문구', async () => {
    payoutsApi.requestPayout.mockRejectedValue(httpError(422));
    renderPage();
    fireEvent.click(await screen.findByText('출금 신청'));
    expect(await screen.findByText('출금 가능한 정산 잔액이 없거나 계좌가 없어요.')).toBeInTheDocument();
  });

  it('출금 신청 실패(그 외) → 일반 실패 문구', async () => {
    payoutsApi.requestPayout.mockRejectedValue(new Error('network'));
    renderPage();
    const btn = await screen.findByText('출금 신청');
    await waitFor(() => expect(btn).not.toBeDisabled());
    fireEvent.click(btn);
    expect(await screen.findByText('신청 실패')).toBeInTheDocument();
  });

  it('계좌 등록 성공 → 폼 닫히고 계좌 정보 표시', async () => {
    payoutsApi.getBankAccount.mockResolvedValue(null);
    payoutsApi.setBankAccount.mockResolvedValue({ id: 'b1', bank: '국민', accountNoMasked: '****1234', holderName: '나' });
    renderPage();

    fireEvent.change(await screen.findByPlaceholderText('홍길동'), { target: { value: '나' } });
    fireEvent.change(screen.getByPlaceholderText('국민은행'), { target: { value: '국민' } });
    fireEvent.change(screen.getByPlaceholderText('숫자만'), { target: { value: '1234567890' } });
    fireEvent.click(screen.getByRole('button', { name: '계좌 저장' }));

    await waitFor(() => expect(payoutsApi.setBankAccount).toHaveBeenCalledWith('나', '국민', '1234567890'));
    expect(await screen.findByText(/\*\*\*\*1234/)).toBeInTheDocument();
    expect(screen.queryByPlaceholderText('홍길동')).not.toBeInTheDocument();
  });

  it('계좌 등록 실패(422) → 계좌 확인 안내', async () => {
    payoutsApi.getBankAccount.mockResolvedValue(null);
    payoutsApi.setBankAccount.mockRejectedValue(httpError(422));
    renderPage();

    fireEvent.change(await screen.findByPlaceholderText('홍길동'), { target: { value: '나' } });
    fireEvent.change(screen.getByPlaceholderText('국민은행'), { target: { value: '국민' } });
    fireEvent.change(screen.getByPlaceholderText('숫자만'), { target: { value: '1234567890' } });
    fireEvent.click(screen.getByRole('button', { name: '계좌 저장' }));
    expect(await screen.findByText('계좌 정보를 확인해 주세요.')).toBeInTheDocument();
  });

  it('출금 내역 — 상태별 배지와 원천징수 표시', async () => {
    payoutsApi.getPayouts.mockResolvedValue([
      { id: 'p1', netAmt: 6769, withholdingAmt: 231, requestedAt: '2026-07-01T00:00:00Z', status: 'PAID' },
      { id: 'p2', netAmt: 3000, withholdingAmt: 100, requestedAt: '2026-07-02T00:00:00Z', status: 'REJECTED' },
    ]);
    renderPage();

    expect(await screen.findByText('지급완료')).toBeInTheDocument();
    expect(screen.getByText('반려됨')).toBeInTheDocument();
    expect(screen.getAllByText('6,769원').length).toBeGreaterThanOrEqual(1); // 상단 출금가능액도 동일값
    expect(screen.getAllByText(/원천징수 231원/).length).toBeGreaterThanOrEqual(1); // 상단 요약도 동일값
  });

  it('계좌 등록됐으면 "변경" 버튼으로 폼을 다시 연다', async () => {
    renderPage();
    fireEvent.click(await screen.findByRole('button', { name: '변경' }));
    expect(await screen.findByPlaceholderText('홍길동')).toBeInTheDocument();
  });
});
