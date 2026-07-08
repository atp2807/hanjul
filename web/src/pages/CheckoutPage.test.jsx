import { fireEvent, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { renderWithProviders, authFixture } from '@hanjul/test-utils';
import * as authCtx from '../auth/AuthContext';
import * as ordersApi from '../services/api/orders';
import { CheckoutPage } from './CheckoutPage';

const { setAmount, renderPaymentMethods, renderAgreement, requestPayment, widgets, loadTossPayments } = vi.hoisted(() => {
  const setAmount = vi.fn().mockResolvedValue();
  const renderPaymentMethods = vi.fn().mockResolvedValue();
  const renderAgreement = vi.fn().mockResolvedValue();
  const requestPayment = vi.fn().mockResolvedValue();
  const widgets = vi.fn(() => ({ setAmount, renderPaymentMethods, renderAgreement, requestPayment }));
  const loadTossPayments = vi.fn().mockResolvedValue({ widgets });
  return { setAmount, renderPaymentMethods, renderAgreement, requestPayment, widgets, loadTossPayments };
});
vi.mock('@tosspayments/tosspayments-sdk', () => ({ ANONYMOUS: 'ANONYMOUS', loadTossPayments }));
vi.mock('../auth/AuthContext');
vi.mock('../services/api/orders');

const ORDER = { orderId: 'order-9', amount: 5000, orderName: '테스트책', bookId: 'book-1' };

function renderCheckout(state = ORDER) {
  return renderWithProviders(<CheckoutPage />, { at: { pathname: '/checkout', state } });
}

describe('CheckoutPage 결제위젯', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    authCtx.useAuth.mockReturnValue(authFixture({ user: { id: 'buyer-1', name: '구매자' } }));
    ordersApi.getPaymentConfig.mockResolvedValue({ demo: false, tossClientKey: 'test_gck_abc' });
  });

  it('위젯 로드 → 금액 세팅·결제수단·약관 렌더 → 결제하기 활성', async () => {
    renderCheckout();

    await waitFor(() => expect(renderPaymentMethods).toHaveBeenCalled());
    expect(loadTossPayments).toHaveBeenCalledWith('test_gck_abc');
    expect(widgets).toHaveBeenCalledWith({ customerKey: 'buyer-1' });
    expect(setAmount).toHaveBeenCalledWith({ currency: 'KRW', value: 5000 });
    expect(renderAgreement).toHaveBeenCalled();

    const payBtn = await screen.findByTestId('pay-button');
    await waitFor(() => expect(payBtn).toBeEnabled());
    expect(payBtn).toHaveTextContent('5,000원 결제하기');
  });

  it('결제하기 클릭 → requestPayment(orderId·orderName·successUrl)', async () => {
    renderCheckout();
    const payBtn = await screen.findByTestId('pay-button');
    await waitFor(() => expect(payBtn).toBeEnabled());

    fireEvent.click(payBtn);
    await waitFor(() => expect(requestPayment).toHaveBeenCalled());
    const opts = requestPayment.mock.calls[0][0];
    expect(opts.orderId).toBe('order-9');
    expect(opts.orderName).toBe('테스트책');
    expect(opts.successUrl).toContain('/payment/result');
    expect(opts.successUrl).toContain('bookId=book-1');
    expect(opts.failUrl).toContain('/payment/result');
  });

  it('사용자 취소(USER_CANCEL)면 에러 없이 버튼 복구', async () => {
    requestPayment.mockRejectedValueOnce({ code: 'USER_CANCEL' });
    renderCheckout();
    const payBtn = await screen.findByTestId('pay-button');
    await waitFor(() => expect(payBtn).toBeEnabled());

    fireEvent.click(payBtn);
    await waitFor(() => expect(requestPayment).toHaveBeenCalled());
    expect(screen.queryByTestId('checkout-error')).not.toBeInTheDocument();
    await waitFor(() => expect(payBtn).toBeEnabled());
  });

  it('주문 state 없이 직접 접근 → 안내 + 위젯 로드 안 함', async () => {
    renderCheckout(null);
    expect(await screen.findByTestId('checkout-error')).toHaveTextContent('잘못된 접근');
    expect(loadTossPayments).not.toHaveBeenCalled();
  });

  it('데모 설정이면 위젯 못 띄우고 안내(방어)', async () => {
    ordersApi.getPaymentConfig.mockResolvedValue({ demo: true, tossClientKey: '' });
    renderCheckout();
    expect(await screen.findByTestId('checkout-error')).toHaveTextContent('결제 설정');
    expect(loadTossPayments).not.toHaveBeenCalled();
  });
});
