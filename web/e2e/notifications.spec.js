import { expect, test } from '@playwright/test';

import { login } from './helpers.js';

async function tokenFor(request, email) {
  const res = await request.get(`/api/auth/test-login?email=${encodeURIComponent(email)}`, { maxRedirects: 0 });
  return new URLSearchParams(res.headers()['location'].split('#')[1]).get('token');
}

// 작가 계정 + 가격만 매긴 DRAFT 책(아직 미출판) 시드 → (작가id, 책id) 반환.
async function seedAuthorWithDraft(request, email, title, price) {
  const token = await tokenFor(request, email);
  const auth = { Authorization: `Bearer ${token}` };
  const me = await (await request.get('/api/me', { headers: auth })).json();
  const book = await (await request.post('/api/books', { headers: auth, data: { title } })).json();
  await request.post(`/api/books/${book.bookId}/import`, { headers: auth, data: { rawText: '# 1장\n\n본문' } });
  await request.put(`/api/books/${book.bookId}/price`, { headers: auth, data: { amount: price } });
  return { authorId: me.id, bookId: book.bookId, auth };
}

// D6 작가 팔로우 → 신간 알림: 팔로우한 독자만 출판 시 알림함에 신간이 뜬다.
test('작가 팔로우 → 신간 출판 → 알림함에 뜨고 책으로 이동', async ({ page, request }) => {
  const { authorId, bookId, auth } = await seedAuthorWithDraft(
    request,
    'notif-author@x.com',
    '구독신간',
    5000,
  );

  // 독자 로그인 → 작가 페이지에서 팔로우
  await login(page, 'notif-reader@x.com');
  await page.goto(`/authors/${authorId}`);
  await page.getByTestId('follow-btn').click();
  await expect(page.getByTestId('follow-btn')).toHaveText('팔로잉');

  // 팔로우 후 작가가 출판 → 알림 발생
  await request.post(`/api/books/${bookId}/publish-now`, { headers: auth });

  // 알림함 새로고침(폴링 대신 페이지 리로드로 즉시 반영)
  await page.reload();
  await expect(page.getByTestId('notif-badge')).toHaveText('1');
  await page.getByTestId('notif-bell').click();
  await expect(page.getByTestId('notif-item')).toContainText('구독신간');

  // 항목 클릭 → 읽음 + 책 상세로 이동
  await page.getByTestId('notif-item').click();
  await expect(page).toHaveURL(new RegExp(`/books/${bookId}`));
});

// 팔로우 토글: 팔로우 → 언팔로우 시 버튼 라벨이 원래대로 돌아온다.
test('작가 팔로우 → 언팔로우 → 버튼 라벨 복귀', async ({ page, request }) => {
  const { authorId } = await seedAuthorWithDraft(request, 'unfollow-author@x.com', '언팔책', 4000);

  await login(page, 'unfollow-reader@x.com');
  await page.goto(`/authors/${authorId}`);

  await page.getByTestId('follow-btn').click();
  await expect(page.getByTestId('follow-btn')).toHaveText('팔로잉');

  await page.getByTestId('follow-btn').click();
  await expect(page.getByTestId('follow-btn')).toHaveText('＋ 팔로우');
});

// 안읽은 알림 여럿 → '모두 읽음' 클릭 시 배지가 사라진다(0).
test('여러 안읽은 알림 → 모두 읽음 → 배지 0', async ({ page, request }) => {
  // 작가 + 미출판 책 2권
  const token = await tokenFor(request, 'markall-author@x.com');
  const auth = { Authorization: `Bearer ${token}` };
  const me = await (await request.get('/api/me', { headers: auth })).json();
  const drafts = [];
  for (const title of ['모두읽음신간A', '모두읽음신간B']) {
    const book = await (await request.post('/api/books', { headers: auth, data: { title } })).json();
    await request.post(`/api/books/${book.bookId}/import`, { headers: auth, data: { rawText: '# 1장\n\n본문' } });
    await request.put(`/api/books/${book.bookId}/price`, { headers: auth, data: { amount: 3000 } });
    drafts.push(book.bookId);
  }

  // 독자가 팔로우한 뒤 두 권 모두 출판 → 안읽은 알림 2건
  await login(page, 'markall-reader@x.com');
  await page.goto(`/authors/${me.id}`);
  await page.getByTestId('follow-btn').click();
  await expect(page.getByTestId('follow-btn')).toHaveText('팔로잉');

  for (const bookId of drafts) {
    await request.post(`/api/books/${bookId}/publish-now`, { headers: auth });
  }

  await page.reload();
  await expect(page.getByTestId('notif-badge')).toHaveText('2');

  // 알림함 열고 '모두 읽음' → 배지 사라짐
  await page.getByTestId('notif-bell').click();
  await page.getByRole('button', { name: '모두 읽음' }).click();
  await expect(page.getByTestId('notif-badge')).toHaveCount(0);
});

// 팔로우 안 하면 알림이 오지 않는다.
test('팔로우 안 한 독자는 신간 알림을 받지 않는다', async ({ page, request }) => {
  const { bookId, auth } = await seedAuthorWithDraft(request, 'notif-author2@x.com', '미구독신간', 3000);

  await login(page, 'notif-stranger@x.com');
  await request.post(`/api/books/${bookId}/publish-now`, { headers: auth });

  await page.goto('/');
  await page.getByTestId('notif-bell').click();
  await expect(page.getByTestId('notif-panel')).toContainText('알림이 없어요');
  await expect(page.getByTestId('notif-badge')).toHaveCount(0);
});
