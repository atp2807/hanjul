import { apiClient } from './api_client';

// 주문 생성 — 금액·구매자는 서버가 결정 (bookId만 보냄).
// withdrawalConsent = 전자책 청약철회 제한 동의(전자상거래법 §17⑥) — 없으면 서버가 422.
export function createOrder(bookId, channel = 'SELF', withdrawalConsent = false) {
  return apiClient.post('/orders', { bookId, channel, withdrawalConsent });
}

// 결제 확인 — pgTxId = 토스 paymentKey (데모 모드면 'demo' 무관 성공)
export function confirmPayment(orderId, pgTxId = 'demo') {
  return apiClient.post(`/orders/${orderId}/confirm`, { pgTxId });
}

// 결제 위젯 설정 — 공개 clientKey + 데모 여부
export function getPaymentConfig() {
  return apiClient.get('/payments/config');
}

// 환불 — 구매자 본인. 성공 시 서재 권한 회수
export function refundOrder(orderId) {
  return apiClient.post(`/orders/${orderId}/refund`);
}

// 내 서재 (구매한 책)
export function getLibrary() {
  return apiClient.get('/me/library');
}
