import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import * as ordersApi from '../services/api/orders';
import { PaymentResultPage } from './PaymentResultPage';

vi.mock('../services/api/orders');
const navigate = vi.fn();
vi.mock('react-router-dom', async (orig) => ({ ...(await orig()), useNavigate: () => navigate }));

function renderAt(query) {
  return render(
    <MemoryRouter initialEntries={[`/payment/result${query}`]}>
      <PaymentResultPage />
    </MemoryRouter>,
  );
}

describe('PaymentResultPage', () => {
  beforeEach(() => vi.clearAllMocks());

  it('성공: paymentKey → confirm → 읽기로 이동', async () => {
    ordersApi.confirmPayment.mockResolvedValue({});
    renderAt('?paymentKey=pk_1&orderId=order-9&amount=5000&bookId=book-1');
    await waitFor(() => expect(ordersApi.confirmPayment).toHaveBeenCalledWith('order-9', 'pk_1'));
    expect(navigate).toHaveBeenCalledWith('/read/book-1', { replace: true });
  });

  it('실패 코드: confirm 호출 안 하고 사유 표시', async () => {
    renderAt('?code=PAY_PROCESS_CANCELED&message=%EC%B7%A8%EC%86%8C&bookId=book-1');
    expect(await screen.findByTestId('payment-result')).toHaveTextContent('결제 실패');
    expect(ordersApi.confirmPayment).not.toHaveBeenCalled();
  });

  it('승인 실패(402): 사유 표시', async () => {
    ordersApi.confirmPayment.mockRejectedValue(Object.assign(new Error('x'), { status: 402 }));
    renderAt('?paymentKey=pk_1&orderId=order-9&bookId=book-1');
    await waitFor(() => expect(screen.getByTestId('payment-result')).toHaveTextContent('승인에 실패'));
  });
});
