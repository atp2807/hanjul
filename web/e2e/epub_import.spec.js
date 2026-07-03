import { expect, test } from '@playwright/test';
import JSZip from 'jszip';

// 작가의 "현관문": 다른 서점/툴에서 만든 원고(.epub)를 그대로 가져와 편집·출판.
// 디스크 픽스처 없이 테스트 안에서 jszip 으로 즉석 EPUB 버퍼를 구성해 setInputFiles 로 넘긴다.
async function makeEpubBuffer() {
  const zip = new JSZip();
  zip.file('mimetype', 'application/epub+zip');
  zip.file(
    'META-INF/container.xml',
    `<?xml version="1.0"?>
     <container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
       <rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles>
     </container>`,
  );
  zip.file(
    'OEBPS/content.opf',
    `<?xml version="1.0" encoding="utf-8"?>
     <package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="uid">
       <metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>테스트책</dc:title></metadata>
       <manifest>
         <item id="c1" href="ch1.xhtml" media-type="application/xhtml+xml"/>
         <item id="c2" href="ch2.xhtml" media-type="application/xhtml+xml"/>
       </manifest>
       <spine>
         <itemref idref="c1"/>
         <itemref idref="c2"/>
       </spine>
     </package>`,
  );
  zip.file(
    'OEBPS/ch1.xhtml',
    `<?xml version="1.0" encoding="utf-8"?>
     <!DOCTYPE html>
     <html xmlns="http://www.w3.org/1999/xhtml"><head><title>1장 도입</title></head>
       <body><h1>1장 도입</h1><p>첫 문단입니다 <strong>굵게</strong> <em>기울임</em></p></body></html>`,
  );
  zip.file(
    'OEBPS/ch2.xhtml',
    `<?xml version="1.0" encoding="utf-8"?>
     <!DOCTYPE html>
     <html xmlns="http://www.w3.org/1999/xhtml"><head><title>2장 전개</title></head>
       <body><p>둘째 장 본문</p></body></html>`,
  );
  return zip.generateAsync({ type: 'nodebuffer' });
}

test('EPUB 가져오기 → 에디터 반영(헤딩·서식) + 목차 자동(챕터별)', async ({ page }) => {
  await page.goto('/write/epub-import-room');

  const buffer = await makeEpubBuffer();
  await page.locator('input[accept=".epub"]').setInputFiles({
    name: 'sample.epub',
    mimeType: 'application/epub+zip',
    buffer,
  });

  const editor = page.locator('.ProseMirror');
  await expect(editor).toContainText('첫 문단입니다');
  await expect(editor.locator('h1').first()).toHaveText('1장 도입');
  await expect(editor.locator('strong')).toHaveText('굵게'); // 인라인 서식 보존
  await expect(editor.locator('em')).toHaveText('기울임');
  await expect(editor).toContainText('둘째 장 본문'); // spine 순서로 2장 이어붙음

  // 챕터 제목(<title>→h1)이 자동 목차로 — 2장은 body 헤딩이 없어 <title> 이 h1 로 보강됨
  await expect(page.getByTestId('outline')).toContainText('1장 도입');
  await expect(page.getByTestId('outline')).toContainText('2장 전개');
});
