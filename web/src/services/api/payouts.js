import { apiClient } from './api_client';

// 작가 출금계좌
export function getBankAccount() {
  return apiClient.get('/me/bank-account');
}
export function setBankAccount(holderName, bank, accountNo) {
  return apiClient.put('/me/bank-account', { holderName, bank, accountNo });
}

// 출금 가능액(미지급 정산 집계)
export function getPayable() {
  return apiClient.get('/me/payouts/payable');
}
// 출금 신청
export function requestPayout() {
  return apiClient.post('/me/payouts');
}
// 출금 내역
export function getPayouts() {
  return apiClient.get('/me/payouts');
}
