import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('../api', () => ({
  api: { orders: vi.fn(), refundOrder: vi.fn() },
}));

import { api } from '../api';
import Refunds from './Refunds';

const orders = [
  {
    id: 'o1', bookId: 'b1', bookTitle: '결제완료된 책', buyerAccountId: 'buyer-1',
    amountAmt: 12000, channel: 'SELF', status: 'PAID',
    createdAt: '2026-07-01T00:00:00Z', paidAt: '2026-07-01T00:05:00Z',
  },
];

beforeEach(() => {
  vi.clearAllMocks();
  api.orders.mockResolvedValue(orders);
  api.refundOrder.mockResolvedValue(null);
});

describe('Refunds (운영자 환불 관리)', () => {
  it('결제완료 주문을 책제목·구매자·금액과 함께 보여준다', async () => {
    render(<Refunds />);
    expect(await screen.findByText('결제완료된 책')).toBeInTheDocument();
    expect(screen.getByText(/구매자 buyer-1/)).toBeInTheDocument();
    expect(screen.getByText(/12,000원/)).toBeInTheDocument();
  });

  it('PAID 상태로 조회한다', async () => {
    render(<Refunds />);
    await screen.findByText('결제완료된 책');
    expect(api.orders).toHaveBeenCalledWith('PAID');
  });

  it('환불 버튼은 사유 프롬프트를 받아 refundOrder를 호출하고 목록을 다시 불러온다', async () => {
    vi.spyOn(window, 'prompt').mockReturnValue('구매자 요청');
    render(<Refunds />);
    fireEvent.click(await screen.findByRole('button', { name: '환불' }));
    await waitFor(() => expect(api.refundOrder).toHaveBeenCalledWith('o1', '구매자 요청'));
    await waitFor(() => expect(api.orders.mock.calls.length).toBeGreaterThanOrEqual(2));
  });

  it('프롬프트 취소(null) 시 refundOrder를 호출하지 않는다', async () => {
    vi.spyOn(window, 'prompt').mockReturnValue(null);
    render(<Refunds />);
    fireEvent.click(await screen.findByRole('button', { name: '환불' }));
    expect(api.refundOrder).not.toHaveBeenCalled();
  });

  it('409(이미 환불/미결제)는 안내 문구를 보여주고 목록을 갱신한다', async () => {
    vi.spyOn(window, 'prompt').mockReturnValue('사유');
    api.refundOrder.mockRejectedValue({ status: 409 });
    render(<Refunds />);
    fireEvent.click(await screen.findByRole('button', { name: '환불' }));
    expect(await screen.findByText('이미 환불되었거나 결제되지 않은 주문입니다. 목록을 갱신했어요.')).toBeInTheDocument();
    await waitFor(() => expect(api.orders.mock.calls.length).toBeGreaterThanOrEqual(2));
  });

  it('402(PG 취소 실패)는 별도 안내 문구를 보여준다', async () => {
    vi.spyOn(window, 'prompt').mockReturnValue('사유');
    api.refundOrder.mockRejectedValue({ status: 402 });
    render(<Refunds />);
    fireEvent.click(await screen.findByRole('button', { name: '환불' }));
    expect(await screen.findByText('PG 취소에 실패했습니다. 잠시 후 다시 시도하세요.')).toBeInTheDocument();
  });

  it('빈 목록이면 안내를 보여준다', async () => {
    api.orders.mockResolvedValue([]);
    render(<Refunds />);
    expect(await screen.findByText('결제완료 주문이 없습니다.')).toBeInTheDocument();
  });
});
