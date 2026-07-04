import { expect, test } from '@playwright/test';

import { login } from './helpers';

// 작가의 "현관문": PDF 원고를 그대로 가져와 편집·출판. DOCX/EPUB 과 달리 서버(pymupdf)가
// 텍스트·서식을 추출하므로 로그인이 필요하다. 디스크 픽스처 없이 Chromium 내장 page.pdf()
// 로 HTML 을 즉석 PDF 버퍼로 렌더링해 setInputFiles 로 넘긴다.
//
// 굵게/기울임(strong/em) 추출은 여기서 검증하지 않는다 — Chromium 헤드리스 print-to-PDF는
// 기본 시스템 폰트에 진짜 별도 Bold/Italic 폰트 리소스를 심지 않고 시각적으로만 두껍게
// 그리는 경우가 많아, PDF 폰트 flags 비트가 안 잡힐 수 있다(실제 한글/워드가 PDF로 저장할
// 때는 실제 Bold 폰트를 심으므로 이 문제가 없음). 그 판정 로직 자체는
// backend/tests/engine/test_pdf_import.py 가 PyMuPDF로 직접 만든 진짜 Bold/Italic 폰트
// 픽스처로 검증한다 — 여기서는 업로드→파싱→에디터 반영까지의 전체 배관(문단·헤딩)만 확인.
async function makePdfBuffer(browser) {
  const page = await browser.newPage();
  // 폰트 크기로 헤딩 판정 → h1 은 큰 글씨.
  await page.setContent(
    `<h1 style="font-size:32px">제목입니다</h1>
     <p style="font-size:16px">첫 문단입니다</p>`,
  );
  const buffer = await page.pdf({ printBackground: true });
  await page.close();
  return buffer;
}

test('PDF 가져오기 → 에디터 반영(문단·헤딩 전체 배관 확인)', async ({ page, browser }) => {
  await login(page, 'pdf-import@example.com');

  const buffer = await makePdfBuffer(browser);

  await page.goto('/write/pdf-import-room');
  await page.locator('input[accept=".pdf"]').setInputFiles({
    name: 'sample.pdf',
    mimeType: 'application/pdf',
    buffer,
  });

  const editor = page.locator('.ProseMirror');
  await expect(editor).toContainText('첫 문단입니다');
  await expect(editor.locator('h1').first()).toContainText('제목입니다');
});
