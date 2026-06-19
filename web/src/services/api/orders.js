import { apiClient } from './api_client';

// 주문 생성 — 금액·구매자는 서버가 결정 (bookId만 보냄)
export function createOrder(bookId, channel = 'SELF') {
  return apiClient.post('/orders', { bookId, channel });
}

// 결제 확인 — 데모 모드면 pgTxId 무관 성공
export function confirmPayment(orderId, pgTxId = 'demo') {
  return apiClient.post(`/orders/${orderId}/confirm`, { pgTxId });
}

// 내 서재 (구매한 책)
export function getLibrary() {
  return apiClient.get('/me/library');
}
