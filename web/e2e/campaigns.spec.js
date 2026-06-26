import { expect, test } from '@playwright/test';

import { login, seedPublishedBook } from './helpers.js';

async function tokenFor(request, email, name = '유저') {
  const res = await request.get(
    `/api/auth/test-login?email=${encodeURIComponent(email)}&name=${encodeURIComponent(name)}`,
    { maxRedirects: 0 },
  );
  return new URLSearchParams(res.headers()['location'].split('#')[1]).get('token');
}

// 작가가 스튜디오에서 서평단 캠페인을 만든다 → 관리 테이블에 노출.
test('작가 서평단 캠페인 생성 (스튜디오)', async ({ page, request }) => {
  const email = 'camp-author@x.com';
  await seedPublishedBook(request, { authorEmail: email, title: '서평단책UI', price: 8000 });

  await login(page, email, '캠작가');
  await page.goto('/studio/campaigns');
  await page.getByRole('button', { name: /새 캠페인/ }).click();
  await expect(page.getByText('새 서평단 캠페인')).toBeVisible();
  await page.getByRole('button', { name: '캠페인 게시' }).click();

  // 관리 테이블에 캠페인 행(책 제목 + 모집중)
  await expect(page.getByText('서평단책UI').first()).toBeVisible();
  await expect(page.getByText('모집중').first()).toBeVisible();
});

// 핵심 여정: 모집 피드 → 신청 → 배정 → 증정본 리뷰 → '서평단' 배지.
test('서평단 풀 흐름 — 신청→배정→증정본 리뷰→배지', async ({ page, request }) => {
  const authorEmail = 'flow-author@x.com';
  const bookId = await seedPublishedBook(request, { authorEmail, title: '증정본흐름책', price: 6000 });
  const aAuth = { Authorization: `Bearer ${await tokenFor(request, authorEmail, '흐름작가')}` };

  // 캠페인 생성(최소분량 작게)
  const camp = await (
    await request.post('/api/campaigns', { headers: aAuth, data: { bookId, slots: 1, reviewDays: 14, minChars: 5 } })
  ).json();
  const cid = camp.campaignId;

  // 독자: 모집 피드에서 발견 → 상세 → 신청
  await login(page, 'flow-reader@x.com', '흐름리뷰어');
  await page.goto('/reviewers');
  await expect(page.getByText('증정본흐름책')).toBeVisible();
  await page.goto(`/campaigns/${cid}`);
  await page.getByRole('button', { name: '리뷰어 신청하기' }).click();
  await expect(page.getByText('✓ 신청 완료')).toBeVisible();

  // 작가: 신청자 배정(증정본 지급)
  const applicants = await (await request.get(`/api/campaigns/${cid}/applications`, { headers: aAuth })).json();
  const applicantId = applicants.items[0].applicantId;
  await request.post(`/api/campaigns/${cid}/assign`, { headers: aAuth, data: { applicantId } });

  // 독자: 내 활동에서 배정 확인 → 증정본 리뷰 작성
  await page.goto('/reviewer/activity');
  await expect(page.getByText('배정됨').first()).toBeVisible();
  await page.getByRole('button', { name: '리뷰 쓰기' }).click();
  await expect(page).toHaveURL(new RegExp(`/campaigns/${cid}/review`));

  await page.getByText('★', { exact: true }).nth(4).click(); // 별 5점
  await page.getByPlaceholder('이 책을 솔직하게 평가해 주세요.').fill('출간 전 먼저 읽었어요. 좋았습니다.');
  await page.getByRole('button', { name: '리뷰 제출' }).click();

  // 책 상세로 이동 + 리뷰에 '서평단' 배지
  await expect(page).toHaveURL(new RegExp(`/books/${bookId}`));
  await expect(page.getByTestId('review-list')).toContainText('출간 전 먼저 읽었어요');
  await expect(page.getByTestId('review-list')).toContainText('서평단');
});
