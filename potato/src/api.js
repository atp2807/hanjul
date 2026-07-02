// 운영자(potato) API — @hanjul/lib 공용 팩토리로 생성. 토큰키 potato_token(고객과 분리).
import { createApiClient } from '@hanjul/lib';

const client = createApiClient('potato_token');

export const getToken = client.getToken;
export const setToken = client.setToken;

const get = client.get;
const post = client.post;

export const api = {
  login: (email, password) => post('/potato/auth/login', { email, password }),
  me: () => get('/potato/auth/me'),
  dashboard: () => get('/potato/dashboard/stats'),

  books: ({ status = '', q = '' } = {}) => {
    const p = new URLSearchParams();
    if (status) p.set('status', status);
    if (q) p.set('q', q);
    const qs = p.toString();
    return get(`/potato/books${qs ? `?${qs}` : ''}`);
  },
  takedown: (id, reason) => post(`/potato/books/${id}/takedown`, { reason }),
  restore: (id) => post(`/potato/books/${id}/restore`),

  reports: (status = 'OPEN') => get(`/potato/reports?status=${status}`),
  resolveReport: (id, action, resolution) =>
    post(`/potato/reports/${id}/resolve`, { action, resolution }),

  account: (id) => get(`/potato/accounts/${id}`),
  suspend: (id, reason) => post(`/potato/accounts/${id}/suspend`, { reason }),
  unsuspend: (id) => post(`/potato/accounts/${id}/unsuspend`),
  blockReview: (id, reason) => post(`/potato/accounts/${id}/block-review`, { reason }),
  unblockReview: (id) => post(`/potato/accounts/${id}/unblock-review`),

  payouts: (status = 'REQUESTED') => get(`/potato/payouts?status=${status}`),
  approvePayout: (id) => post(`/potato/payouts/${id}/approve`),
  payPayout: (id, reason) => post(`/potato/payouts/${id}/pay`, { reason }),
  rejectPayout: (id, reason) => post(`/potato/payouts/${id}/reject`, { reason }),
};
