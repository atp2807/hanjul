import { expect } from '@playwright/test';

// test-login 우회로 브라우저 세션 로그인 → 홈으로 정착할 때까지 대기.
// 백엔드가 /auth/callback#token=... 로 302 → AuthCallbackPage가 토큰 저장 후 '/'로 이동.
export async function login(page, email, name = '테스트작가') {
  const q = new URLSearchParams({ email, name });
  await page.goto(`/api/auth/test-login?${q.toString()}`);
  await expect(page.getByRole('button', { name: '로그아웃' })).toBeVisible();
}

/**
 * test-login 302 응답의 location 프래그먼트(#token=...)에서 JWT를 뽑아온다. UI 로그인(login()) 없이
 * API만으로 인증 헤더가 필요할 때 사용 — checklist/schedule_publish/delete_book/content_rating/
 * notifications/reader_pagination/store_search/doc_flow.spec.js 각각에 흩어져 있던 로컬
 * `tokenFor(request, email[, name])` 재발명들과 동일 계약(name 기본값 '테스트작가'는 백엔드
 * test-login 엔드포인트의 기본값과 같아, name을 아예 안 보내던 변형들과도 결과가 같다).
 * @param {import('@playwright/test').APIRequestContext} request
 * @param {string} email
 * @param {string} [name='테스트작가']
 * @returns {Promise<string>} JWT
 */
export async function tokenFor(request, email, name = '테스트작가') {
  const res = await request.get(
    `/api/auth/test-login?email=${encodeURIComponent(email)}&name=${encodeURIComponent(name)}`,
    { maxRedirects: 0 },
  );
  const loc = res.headers()['location'];
  return new URLSearchParams(loc.split('#')[1]).get('token');
}

/**
 * 작가(임의 유저) 세션 일괄 준비 — 토큰 발급 + `/api/me` 조회로 계정 id까지 얻는다.
 * notifications.spec.js의 `seedAuthorWithDraft`가 앞부분에서 하던 "토큰 발급 → /api/me"를
 * 떼어낸 것 — authorId가 필요한 시나리오(작가 팔로우 등)에서 seedBook({auth})과 조합해 쓴다.
 * @param {import('@playwright/test').APIRequestContext} request
 * @param {string} email
 * @param {string} [name='테스트작가']
 * @returns {Promise<{authorId: string, auth: {Authorization: string}, token: string}>}
 */
export async function authorSession(request, email, name = '테스트작가') {
  const token = await tokenFor(request, email, name);
  const auth = { Authorization: `Bearer ${token}` };
  const me = await (await request.get('/api/me', { headers: auth })).json();
  return { authorId: me.id, auth, token };
}

/**
 * 책 시드 통합 함수 — 기존 로컬 변형들(seedDraftBook·content_rating.spec.js의 seedBook·
 * seedAuthorWithDraft·seedLongFreeBook·seedWithCategory) + 기존 중앙 seedPublishedBook을
 * 파라미터화 하나로 흡수한다. 항상: 책 생성 → 원고 가져오기 → (가격) → (분류) → (발행) 순.
 * @param {import('@playwright/test').APIRequestContext} request
 * @param {object} p
 * @param {string} [p.authorEmail] - 작가 이메일. `auth`를 안 넘기면 이걸로 tokenFor 발급.
 * @param {{Authorization: string}} [p.auth] - 이미 발급된 인증 헤더(authorSession() 등에서 재사용).
 *   넘기면 authorEmail로 새로 토큰을 따지 않는다(같은 작가로 책 여러 권 시드할 때 유용).
 * @param {string} p.title - 책 제목.
 * @param {string} p.rawText - `/import`로 넣을 원고 본문.
 * @param {number|null} [p.price=null] - 가격. null이면 가격 미설정 상태로 남긴다(체크리스트 미충족 등).
 * @param {string|null} [p.category=null] - 분류(장르). null이면 미설정.
 * @param {boolean} [p.publish=price!==null] - true면 `/publish-now`까지 호출.
 *   기본값은 "가격이 있으면 발행"이지만, 가격은 있으나 아직 미출판이어야 하는 시나리오
 *   (예약 발행 전 상태, 삭제 대상 DRAFT 등)는 반드시 `publish: false`를 명시로 넘겨야 한다.
 * @returns {Promise<string>} bookId
 */
export async function seedBook(
  request,
  { authorEmail, auth, title, rawText, price = null, category = null, publish = price !== null },
) {
  const authHeader = auth ?? { Authorization: `Bearer ${await tokenFor(request, authorEmail)}` };

  const book = await (await request.post('/api/books', { headers: authHeader, data: { title } })).json();
  const id = book.bookId;
  await request.post(`/api/books/${id}/import`, { headers: authHeader, data: { rawText } });
  if (price !== null) {
    await request.put(`/api/books/${id}/price`, { headers: authHeader, data: { amount: price } });
  }
  if (category !== null) {
    await request.put(`/api/books/${id}/meta`, { headers: authHeader, data: { category } });
  }
  if (publish) {
    await request.post(`/api/books/${id}/publish-now`, { headers: authHeader });
  }
  return id;
}

/**
 * 무작위 유니크 이메일 생성 — 같은 스위트 내 다른 spec과 계정이 겹치지 않게(고정 이메일 재사용 시
 * 표시 이름·팔로우 상태 등이 테스트 간에 오염될 수 있다). helpers.spec.js 스모크 테스트용으로 추가.
 * @param {string} label - 이메일 로컬파트 접두어(가독성용, 예: 'smoke-draft').
 * @returns {string}
 */
export function uniqueEmail(label) {
  return `${label}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}@e2e.hanjul.io`;
}

// API로 출판본 1권 시드 (소비자 구매 여정의 전제). 작가 토큰을 request로 발급해 사용.
// 시그니처·동작(가져오기 본문 '# 1장\n\n본문입니다.', 항상 발행)은 그대로 두고 내부만 seedBook 위임.
export async function seedPublishedBook(request, { authorEmail, title, price }) {
  return seedBook(request, {
    authorEmail,
    title,
    rawText: '# 1장\n\n본문입니다.',
    price,
    publish: true,
  });
}
