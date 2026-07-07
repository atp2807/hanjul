import { expect, test } from '@playwright/test';

import { login, seedPublishedBook, tokenFor } from './helpers.js';

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

// 신청 후 배정 전(PENDING)이면 독자가 스스로 신청을 취소할 수 있다.
test('서평단 신청 취소 — 내 활동에서 신청 철회', async ({ page, request }) => {
  const authorEmail = 'cancel-author@x.com';
  const bookId = await seedPublishedBook(request, { authorEmail, title: '신청취소책', price: 6000 });
  const aAuth = { Authorization: `Bearer ${await tokenFor(request, authorEmail, '취소작가')}` };

  const camp = await (
    await request.post('/api/campaigns', { headers: aAuth, data: { bookId, slots: 1, reviewDays: 14, minChars: 5 } })
  ).json();
  const cid = camp.campaignId;

  // 독자: 신청
  await login(page, 'cancel-reader@x.com', '취소리뷰어');
  await page.goto(`/campaigns/${cid}`);
  await page.getByRole('button', { name: '리뷰어 신청하기' }).click();
  await expect(page.getByText('신청 완료')).toBeVisible();

  // 내 활동: 대기(PENDING) 항목 확인 → 신청 취소
  await page.goto('/reviewer/activity');
  await expect(page.getByText('신청취소책')).toBeVisible();
  await page.getByRole('button', { name: '신청 취소' }).click();

  // 신청 목록에서 사라짐 → 활동 없음 안내
  await expect(page.getByText('신청취소책')).toHaveCount(0);
  await expect(page.getByText('아직 활동이 없어요')).toBeVisible();
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
  await expect(page.getByText('신청 완료')).toBeVisible();

  // 작가: 신청자 배정(증정본 지급)
  const applicants = await (await request.get(`/api/campaigns/${cid}/applications`, { headers: aAuth })).json();
  const applicantId = applicants.items[0].applicantId;
  await request.post(`/api/campaigns/${cid}/assign`, { headers: aAuth, data: { applicantId } });

  // 독자: 내 활동에서 배정 확인 → 증정본 리뷰 작성
  await page.goto('/reviewer/activity');
  await expect(page.getByText('배정됨').first()).toBeVisible();
  await page.getByRole('button', { name: '리뷰 쓰기' }).click();
  await expect(page).toHaveURL(new RegExp(`/campaigns/${cid}/review`));

  await page.getByRole('button', { name: '별점 5점' }).click(); // 별 5점
  await page.getByPlaceholder('이 책을 솔직하게 평가해 주세요.').fill('출간 전 먼저 읽었어요. 좋았습니다.');
  await page.getByRole('button', { name: '리뷰 제출' }).click();

  // 책 상세로 이동 + 리뷰에 '서평단' 배지
  await expect(page).toHaveURL(new RegExp(`/books/${bookId}`));
  await expect(page.getByTestId('review-list')).toContainText('출간 전 먼저 읽었어요');
  await expect(page.getByTestId('review-list')).toContainText('서평단');
});

// 작가가 OPEN 캠페인을 수동 마감 → 상태 라벨이 '모집중'→'리뷰중'(CLOSED)으로 바뀐다.
test('작가 캠페인 마감 — 모집중 → 리뷰중', async ({ page, request }) => {
  const authorEmail = 'close-author@x.com';
  const bookId = await seedPublishedBook(request, { authorEmail, title: '마감책', price: 7000 });
  const aAuth = { Authorization: `Bearer ${await tokenFor(request, authorEmail, '마감작가')}` };

  await request.post('/api/campaigns', {
    headers: aAuth,
    data: { bookId, slots: 3, reviewDays: 14, minChars: 5 },
  });

  await login(page, authorEmail, '마감작가');
  await page.goto('/studio/campaigns');

  // OPEN 상태 = 모집중 + '마감' 버튼 노출
  await expect(page.getByText('마감책').first()).toBeVisible();
  await expect(page.getByText('모집중').first()).toBeVisible();
  await page.getByRole('button', { name: '마감' }).click();

  // CLOSED 로 전환 → '리뷰중' 라벨, '모집중' 사라짐
  await expect(page.getByText('리뷰중').first()).toBeVisible();
  await expect(page.getByText('모집중')).toHaveCount(0);
});
