import { expect, test } from '@playwright/test';

import { authorSession, seedBook, tokenFor, uniqueEmail } from './helpers.js';

// helpers.js 신설 함수들의 스모크 테스트 — API 전용(page 불필요), 실 백엔드 상대로 동작 검증.
// 이 스위트가 회귀 가드 역할: 향후 helpers.js를 손대도 여기가 먼저 깨진다.

// GET /api/me/books 응답에서 seedBook으로 만든 책 하나를 찾는다.
async function findMyBook(request, auth, bookId) {
  const list = await (await request.get('/api/me/books', { headers: auth })).json();
  return list.items.find((b) => b.id === bookId);
}

test('tokenFor — test-login 리다이렉트에서 유효한 JWT를 뽑아온다', async ({ request }) => {
  const email = uniqueEmail('smoke-token');
  const token = await tokenFor(request, email, '스모크토큰');
  expect(typeof token).toBe('string');
  expect(token.length).toBeGreaterThan(10);

  // 발급받은 토큰으로 /api/me가 실제로 인증돼야 의미가 있다.
  const me = await request.get('/api/me', { headers: { Authorization: `Bearer ${token}` } });
  expect(me.ok()).toBe(true);
  expect((await me.json()).displayName).toBe('스모크토큰');
});

test('uniqueEmail — 호출마다 다른 이메일을 생성한다', async () => {
  const a = uniqueEmail('smoke-dup');
  const b = uniqueEmail('smoke-dup');
  expect(a).not.toBe(b);
  expect(a).toMatch(/^smoke-dup-.+@e2e\.hanjul\.io$/);
});

test('seedBook — 가격 없이 시드하면 DRAFT로 남고(publish 기본 false) 발행되지 않는다', async ({ request }) => {
  const email = uniqueEmail('smoke-draft');
  const { auth } = await authorSession(request, email, '스모크초안작가');
  const bookId = await seedBook(request, { authorEmail: email, auth, title: '스모크초안책', rawText: '# 1장\n\n본문' });

  const book = await findMyBook(request, auth, bookId);
  expect(book).toBeTruthy();
  expect(book.status).toBe('DRAFT');
  expect(book.priceAmt).toBeNull();
});

test('seedBook — price 지정 시 기본값으로 발행까지 완료된다(publish=price!==null)', async ({ request }) => {
  const email = uniqueEmail('smoke-pub');
  const { auth } = await authorSession(request, email, '스모크발행작가');
  const bookId = await seedBook(request, {
    authorEmail: email,
    auth,
    title: '스모크발행책',
    rawText: '# 1장\n\n본문',
    price: 3000,
  });

  const book = await findMyBook(request, auth, bookId);
  expect(book.status).toBe('PUBLISHED');
  expect(book.priceAmt).toBe(3000);
});

test('seedBook — price + category + publish:false → 가격·분류는 반영되고 미출판 상태를 유지한다', async ({ request }) => {
  const email = uniqueEmail('smoke-cat');
  const { auth, authorId } = await authorSession(request, email, '스모크분류작가');
  const bookId = await seedBook(request, {
    authorEmail: email,
    auth,
    title: '스모크분류책',
    rawText: '# 1장\n\n본문',
    price: 5000,
    category: '소설',
    publish: false,
  });

  expect(authorId).toBeTruthy();
  const book = await findMyBook(request, auth, bookId);
  expect(book.status).toBe('DRAFT');
  expect(book.priceAmt).toBe(5000);
  expect(book.category).toBe('소설');
});
