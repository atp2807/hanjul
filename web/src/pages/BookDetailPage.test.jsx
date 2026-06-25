import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import * as authCtx from '../auth/AuthContext';
import * as booksApi from '../services/api/books';
import * as ordersApi from '../services/api/orders';
import * as reviewsApi from '../services/api/reviews';
import { BookDetailPage } from './BookDetailPage';

const { requestPayment } = vi.hoisted(() => ({ requestPayment: vi.fn() }));
vi.mock('@tosspayments/payment-sdk', () => ({
  loadTossPayments: vi.fn().mockResolvedValue({ requestPayment }),
}));
vi.mock('../auth/AuthContext');
vi.mock('../services/api/books');
vi.mock('../services/api/orders');
vi.mock('../services/api/reviews');
vi.mock('react-router-dom', async (orig) => ({ ...(await orig()), useNavigate: () => vi.fn() }));

const BOOK = { id: 'book-1', title: '테스트책', priceAmt: 5000, authorId: 'a1' };

describe('BookDetailPage 결제', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    authCtx.useAuth.mockReturnValue({ user: { id: 'buyer-1' } });
    booksApi.getStoreDetail.mockResolvedValue(BOOK);
    reviewsApi.getReviews.mockResolvedValue({ average: 0, count: 0, items: [] });
    ordersApi.createOrder.mockResolvedValue({ id: 'order-9', amountAmt: 5000 });
  });

  it('실 결제: 구매 → 토스 결제창(카드) 호출 (orderId·amount·successUrl)', async () => {
    ordersApi.getPaymentConfig.mockResolvedValue({ demo: false, tossClientKey: 'test_ck_abc' });
    render(
      <MemoryRouter>
        <BookDetailPage />
      </MemoryRouter>,
    );
    fireEvent.click(await screen.findByText('구매'));

    await waitFor(() => expect(requestPayment).toHaveBeenCalled());
    const [method, opts] = requestPayment.mock.calls[0];
    expect(method).toBe('카드');
    expect(opts.orderId).toBe('order-9');
    expect(opts.amount).toBe(5000);
    expect(opts.orderName).toBe('테스트책');
    expect(opts.successUrl).toContain('/payment/result');
    expect(opts.successUrl).toContain('bookId=book-1');
    expect(ordersApi.confirmPayment).not.toHaveBeenCalled(); // confirm은 결과페이지에서
  });

  it('데모 모드: 결제창 없이 바로 demo confirm', async () => {
    ordersApi.getPaymentConfig.mockResolvedValue({ demo: true, tossClientKey: '' });
    ordersApi.confirmPayment.mockResolvedValue({});
    render(
      <MemoryRouter>
        <BookDetailPage />
      </MemoryRouter>,
    );
    fireEvent.click(await screen.findByText('구매'));

    await waitFor(() => expect(ordersApi.confirmPayment).toHaveBeenCalledWith('order-9', 'demo'));
    expect(requestPayment).not.toHaveBeenCalled();
  });
});
