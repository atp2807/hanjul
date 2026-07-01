// 운영자(potato) API 클라이언트 — 고객 앱과 분리된 토큰(potato_token).
const BASE = import.meta.env.VITE_API_BASE_URL || '';
const TOKEN_KEY = 'potato_token';

export const getToken = () => localStorage.getItem(TOKEN_KEY);
export const setToken = (t) => {
  if (t) localStorage.setItem(TOKEN_KEY, t);
  else localStorage.removeItem(TOKEN_KEY);
};

async function request(path, options = {}) {
  const token = getToken();
  const res = await fetch(`${BASE}/api${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers || {}),
    },
    ...options,
  });
  if (!res.ok) {
    const err = new Error(`API ${res.status}: ${path}`);
    err.status = res.status;
    throw err;
  }
  if (res.status === 204) return null;
  return res.json();
}

const post = (path, body) =>
  request(path, { method: 'POST', body: body ? JSON.stringify(body) : undefined });

export const api = {
  login: (email, password) => post('/potato/auth/login', { email, password }),
  me: () => request('/potato/auth/me'),
  dashboard: () => request('/potato/dashboard/stats'),

  books: ({ status = '', q = '' } = {}) => {
    const p = new URLSearchParams();
    if (status) p.set('status', status);
    if (q) p.set('q', q);
    const qs = p.toString();
    return request(`/potato/books${qs ? `?${qs}` : ''}`);
  },
  takedown: (id, reason) => post(`/potato/books/${id}/takedown`, { reason }),
  restore: (id) => post(`/potato/books/${id}/restore`),

  reports: (status = 'OPEN') => request(`/potato/reports?status=${status}`),
  resolveReport: (id, action, resolution) =>
    post(`/potato/reports/${id}/resolve`, { action, resolution }),

  account: (id) => request(`/potato/accounts/${id}`),
  suspend: (id, reason) => post(`/potato/accounts/${id}/suspend`, { reason }),
  unsuspend: (id) => post(`/potato/accounts/${id}/unsuspend`),
  blockReview: (id, reason) => post(`/potato/accounts/${id}/block-review`, { reason }),
  unblockReview: (id) => post(`/potato/accounts/${id}/unblock-review`),

  payouts: (status = 'REQUESTED') => request(`/potato/payouts?status=${status}`),
  approvePayout: (id) => post(`/potato/payouts/${id}/approve`),
  payPayout: (id, reason) => post(`/potato/payouts/${id}/pay`, { reason }),
  rejectPayout: (id, reason) => post(`/potato/payouts/${id}/reject`, { reason }),
};
