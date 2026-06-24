import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import * as authCtx from '../auth/AuthContext';
import * as booksApi from '../services/api/books';
import * as ordersApi from '../services/api/orders';
import * as reviewsApi from '../services/api/reviews';
import { BookDetailPage } from './BookDetailPage';

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

  it('실 결제 모드: 구매 클릭 → 토스 위젯 iframe 이 clientKey·orderId·amount 로 열린다', async () => {
    ordersApi.getPaymentConfig.mockResolvedValue({ demo: false, tossClientKey: 'test_ck_abc' });
    render(
      <MemoryRouter>
        <BookDetailPage />
      </MemoryRouter>,
    );
    fireEvent.click(await screen.findByText('구매'));

    const iframe = await screen.findByTestId('payment-iframe');
    const src = iframe.getAttribute('src');
    expect(src).toContain('/payment-widget.html');
    expect(src).toContain('clientKey=test_ck_abc');
    expect(src).toContain('orderId=order-9');
    expect(src).toContain('amount=5000');
    // 위젯이 떴으면 데모 confirm 은 호출되지 않아야 함
    expect(ordersApi.confirmPayment).not.toHaveBeenCalled();
  });

  it('데모 모드: 위젯 없이 바로 demo confirm', async () => {
    ordersApi.getPaymentConfig.mockResolvedValue({ demo: true, tossClientKey: '' });
    ordersApi.confirmPayment.mockResolvedValue({});
    render(
      <MemoryRouter>
        <BookDetailPage />
      </MemoryRouter>,
    );
    fireEvent.click(await screen.findByText('구매'));

    await waitFor(() => expect(ordersApi.confirmPayment).toHaveBeenCalledWith('order-9', 'demo'));
    expect(screen.queryByTestId('payment-iframe')).not.toBeInTheDocument();
  });
});
