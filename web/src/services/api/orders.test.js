import { describe, expect, it, vi } from 'vitest';

import { apiClient } from './api_client';
import { confirmPayment, createOrder, getLibrary, getPaymentConfig, refundOrder } from './orders';

vi.mock('./api_client', () => ({
  apiClient: { get: vi.fn(), post: vi.fn(), put: vi.fn(), del: vi.fn() },
}));

describe('services/api/orders', () => {
  it('createOrder → channel·withdrawalConsent 기본값', () => {
    createOrder('b1');
    expect(apiClient.post).toHaveBeenCalledWith('/orders', { bookId: 'b1', channel: 'SELF', withdrawalConsent: false });
  });

  it('createOrder → 값 지정 시 그대로 서버 전달', () => {
    createOrder('b1', 'EXTERNAL', true);
    expect(apiClient.post).toHaveBeenCalledWith('/orders', { bookId: 'b1', channel: 'EXTERNAL', withdrawalConsent: true });
  });

  it('confirmPayment → pgTxId 기본값 demo', () => {
    confirmPayment('o1');
    expect(apiClient.post).toHaveBeenCalledWith('/orders/o1/confirm', { pgTxId: 'demo' });
  });

  it('confirmPayment → 실 결제 pgTxId 전달', () => {
    confirmPayment('o1', 'toss-tx-1');
    expect(apiClient.post).toHaveBeenCalledWith('/orders/o1/confirm', { pgTxId: 'toss-tx-1' });
  });

  it('getPaymentConfig → GET /payments/config', () => {
    getPaymentConfig();
    expect(apiClient.get).toHaveBeenCalledWith('/payments/config');
  });

  it('refundOrder → POST /orders/:id/refund', () => {
    refundOrder('o1');
    expect(apiClient.post).toHaveBeenCalledWith('/orders/o1/refund');
  });

  it('getLibrary → GET /me/library', () => {
    getLibrary();
    expect(apiClient.get).toHaveBeenCalledWith('/me/library');
  });
});
