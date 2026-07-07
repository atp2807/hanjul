import { describe, expect, it, vi } from 'vitest';

import { mockApiClient } from '@hanjul/test-utils';
import { apiClient } from './api_client';
import { getBankAccount, getPayable, getPayouts, requestPayout, setBankAccount } from './payouts';

vi.mock('./api_client', () => ({
  apiClient: mockApiClient(),
}));

describe('services/api/payouts', () => {
  it('getBankAccount → GET /me/bank-account', () => {
    getBankAccount();
    expect(apiClient.get).toHaveBeenCalledWith('/me/bank-account');
  });

  it('setBankAccount → PUT /me/bank-account', () => {
    setBankAccount('홍길동', '004', '1234567890');
    expect(apiClient.put).toHaveBeenCalledWith('/me/bank-account', { holderName: '홍길동', bank: '004', accountNo: '1234567890' });
  });

  it('getPayable → GET /me/payouts/payable', () => {
    getPayable();
    expect(apiClient.get).toHaveBeenCalledWith('/me/payouts/payable');
  });

  it('requestPayout → POST /me/payouts', () => {
    requestPayout();
    expect(apiClient.post).toHaveBeenCalledWith('/me/payouts');
  });

  it('getPayouts → GET /me/payouts', () => {
    getPayouts();
    expect(apiClient.get).toHaveBeenCalledWith('/me/payouts');
  });
});
