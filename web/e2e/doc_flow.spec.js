// 한줄독(/doc) 사용자 플로우 e2e — 업로드→읽기, 편집 자동저장, 공유링크, 수출, 소유권.
// backend/src/features/doc + web DocsPage/DocPage/DocSharePage 실제 라우트·셀렉터 기준
// (packages/doc 조판 코어 자체의 실측 검증은 doc_typeset.spec.js 가 담당 — 역할 분리).
import { expect, test } from '@playwright/test';

import { login } from './helpers.js';

async function tokenFor(request, email, name = '문서주인') {
  const res = await request.get(
    `/api/auth/test-login?email=${encodeURIComponent(email)}&name=${encodeURIComponent(name)}`,
    { maxRedirects: 0 },
  );
  return new URLSearchParams(res.headers()['location'].split('#')[1]).get('token');
}

// ① 비로그인 업로드(md) → 읽기 — ownerless 문서(owner_id NULL) 허용을 검증.
test('비로그인으로 md 업로드 후 바로 읽을 수 있다', async ({ page }) => {
  await page.goto('/doc');
  const md = '# 제목입니다\n\n본문 문단입니다.';
  await page.locator('input[type=file]').setInputFiles({
    name: 'sample.md',
    mimeType: 'text/markdown',
    buffer: Buffer.from(md),
  });
  await expect(page).toHaveURL(/\/doc\/[0-9a-fA-F-]{8}-/); // DocsPage.jsx:59 navigate(`/doc/${doc.id}`)
  await expect(page.locator('.juldoc-page').first()).toContainText('제목입니다');
});

// ② 편집 → 2초 디바운스 자동저장 확인.
test('편집 내용이 2초 후 자동저장된다', async ({ page }) => {
  await page.goto('/doc');
  await page.locator('input[type=file]').setInputFiles({
    name: 'edit-me.md', mimeType: 'text/markdown', buffer: Buffer.from('# 원본\n\n본문'),
  });
  await expect(page).toHaveURL(/\/doc\//);
  await page.getByRole('button', { name: '편집' }).click(); // DocPage.jsx:167 세그 버튼

  const editor = page.locator('article.juldoc-editor[contenteditable="true"]');
  await editor.click();
  await page.keyboard.type(' 자동저장 확인 문장');

  // '저장 중…'(saving) 은 로컬에선 왕복이 수십 ms 라 폴링 사이에 지나가 단언 불가(flaky) —
  // 종착 상태 '저장됨'(DocPage.jsx:87 onStatus('saved'))만 단언한다. 2초 디바운스+왕복 여유.
  await expect(page.getByText('저장됨')).toBeVisible({ timeout: 5000 });

  await page.reload();
  await page.getByRole('button', { name: '편집' }).click();
  await expect(page.locator('article.juldoc-editor')).toContainText('자동저장 확인 문장');
});

// ③ view 권한 공유링크 발급 → 새 브라우저 컨텍스트에서 열람(클립보드 API 미의존 — 패널 목록에서 URL 직접 읽음).
test('view 권한 공유링크를 새 브라우저 컨텍스트에서 열람할 수 있다', async ({ page, browser }) => {
  await page.goto('/doc');
  await page.locator('input[type=file]').setInputFiles({
    name: 'share-me.md', mimeType: 'text/markdown', buffer: Buffer.from('# 공유 문서\n\n내용'),
  });
  await expect(page).toHaveURL(/\/doc\//);

  await page.getByRole('button', { name: '공유' }).click(); // DocPage.jsx:169
  // 권한 select 기본값이 이미 'view'(DocPage.jsx:43 useState('view')) — 그대로 발급
  await page.getByRole('button', { name: '링크 발급' }).click(); // 186행
  const urlSpan = page.locator('li span[style*="monospace"]').first(); // 198행 url span
  await expect(urlSpan).toBeVisible();
  const shareUrl = await urlSpan.innerText();

  const guest = await browser.newContext();
  const guestPage = await guest.newPage();
  await guestPage.goto(shareUrl);
  await expect(guestPage.locator('.juldoc-page').first()).toContainText('공유 문서');
  // view 권한이라 편집 토글이 없어야 함(DocSharePage.jsx:91-96 canEdit=false 면 세그 버튼 자체가 없음)
  await expect(guestPage.getByRole('button', { name: '편집' })).toHaveCount(0);
  await guest.close();
});

// ④ EPUB/DOCX 수출 다운로드 이벤트.
// ⚠️ 스펙 초안은 <a href download> 앵커를 가정했으나, 실제 DocPage.jsx:170-171 은
// 버튼 + apiClient.download(blob fetch → 인증 첨부, packages/lib/src/apiClient.js:47-64)로
// 바뀌어 있다(exportEpub 이 mine 문서 403 결함을 고치기 위한 리팩터 — docs.js:134-135 주석).
// 다운로드는 여전히 blob URL + <a download> 클릭으로 트리거되므로 Playwright download
// 이벤트는 동일하게 발생(author.spec.js 'EPUB 내려받기' 버튼과 같은 메커니즘).
test('EPUB로 내보내기 시 다운로드가 발생한다', async ({ page }) => {
  await page.goto('/doc');
  await page.locator('input[type=file]').setInputFiles({
    name: 'export-me.md', mimeType: 'text/markdown', buffer: Buffer.from('# 내보내기\n\n본문'),
  });
  await expect(page).toHaveURL(/\/doc\//);
  const [download] = await Promise.all([
    page.waitForEvent('download'),
    page.getByRole('button', { name: 'EPUB', exact: true }).click(), // DocPage.jsx:170
  ]);
  expect(download.suggestedFilename()).toMatch(/\.epub$/);
});

test('DOCX로 내보내기 시 다운로드가 발생한다', async ({ page }) => {
  await page.goto('/doc');
  await page.locator('input[type=file]').setInputFiles({
    name: 'export-me-docx.md', mimeType: 'text/markdown', buffer: Buffer.from('# 내보내기\n\n본문'),
  });
  await expect(page).toHaveURL(/\/doc\//);
  const [download] = await Promise.all([
    page.waitForEvent('download'),
    page.getByRole('button', { name: 'DOCX', exact: true }).click(), // DocPage.jsx:171
  ]);
  expect(download.suggestedFilename()).toMatch(/\.docx$/);
});

// ⑤ 소유권 — 로그인 사용자가 만든 문서를 다른 계정이 편집 시도하면 403.
// (실제 라우트는 PUT /api/documents/{id}/html — docs.js:71-73 saveDocumentHtml,
// backend endpoints.py:166-175, document_service.py:90-99 ensure_can_modify)
test('로그인 사용자가 만든 문서는 다른 계정으로 편집 시 403', async ({ page, request }) => {
  await login(page, 'doc-owner@x.com', '문서주인');
  await page.goto('/doc');
  await page.locator('input[type=file]').setInputFiles({
    name: 'owned.md', mimeType: 'text/markdown', buffer: Buffer.from('# 소유 문서\n\n내용'),
  });
  await expect(page).toHaveURL(/\/doc\/([0-9a-fA-F-]+)$/);
  const docId = page.url().match(/\/doc\/([0-9a-fA-F-]+)$/)[1];

  const intruderAuth = { Authorization: `Bearer ${await tokenFor(request, 'doc-intruder@x.com', '침입자')}` };
  const res = await request.put(`/api/documents/${docId}/html`, {
    headers: intruderAuth,
    data: { html: '<article data-juldoc><p>hack</p></article>' },
  });
  expect(res.status()).toBe(403);
});
