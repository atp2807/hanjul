import { expect } from '@playwright/test';

// test-login 우회로 브라우저 세션 로그인 → 홈으로 정착할 때까지 대기.
// 백엔드가 /auth/callback#token=... 로 302 → AuthCallbackPage가 토큰 저장 후 '/'로 이동.
export async function login(page, email, name = '테스트작가') {
  const q = new URLSearchParams({ email, name });
  await page.goto(`/api/auth/test-login?${q.toString()}`);
  await expect(page.getByRole('button', { name: '로그아웃' })).toBeVisible();
}

// API로 출판본 1권 시드 (소비자 구매 여정의 전제). 작가 토큰을 request로 발급해 사용.
export async function seedPublishedBook(request, { authorEmail, title, price }) {
  // 토큰 추출 — 리다이렉트 fragment에서
  const res = await request.get(`/api/auth/test-login?email=${encodeURIComponent(authorEmail)}`, {
    maxRedirects: 0,
  });
  const loc = res.headers()['location'];
  const token = new URLSearchParams(loc.split('#')[1]).get('token');
  const auth = { Authorization: `Bearer ${token}` };

  const book = await (await request.post('/api/books', { headers: auth, data: { title } })).json();
  const id = book.bookId;
  await request.post(`/api/books/${id}/import`, { headers: auth, data: { rawText: '# 1장\n\n본문입니다.' } });
  await request.put(`/api/books/${id}/price`, { headers: auth, data: { amount: price } });
  await request.post(`/api/books/${id}/publish-now`, { headers: auth });
  return id;
}
