import { expect, test } from '@playwright/test';
import JSZip from 'jszip';

import { login } from './helpers';

// HWP/HWPX 가져오기: DOCX/EPUB 와 달리 서버 파싱(hwp-hwpx-parser, 파이썬)이라 로그인 필요.
// 디스크 픽스처 없이 테스트 안에서 jszip 으로 유효 HWPX 버퍼를 구성(build_hwpx 파이썬 포팅).
// hwp-hwpx-parser.Reader 가 이 버퍼를 문단 리스트로 정확히 분리해 읽는 것을 백엔드에서 실측 검증함.
const NS_HH = 'http://www.hancom.co.kr/hwpml/2011/head';
const NS_HC = 'http://www.hancom.co.kr/hwpml/2011/core';
const NS_HS = 'http://www.hancom.co.kr/hwpml/2011/section';
const NS_HP = 'http://www.hancom.co.kr/hwpml/2011/paragraph';
const NS_OCF = 'urn:oasis:names:tc:opendocument:xmlns:container';
const NS_HPF = 'http://www.hancom.co.kr/schema/2011/hpf';

async function buildHwpx(paragraphs) {
  const containerXml =
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
    `<ocf:container xmlns:ocf="${NS_OCF}" xmlns:hpf="${NS_HPF}"><ocf:rootfiles>` +
    '<ocf:rootfile full-path="Contents/content.hpf" media-type="application/hwpml-package+xml"/></ocf:rootfiles></ocf:container>';

  const contentHpf =
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
    `<hpf:package xmlns:hpf="${NS_HPF}" xmlns:opf="http://www.idpf.org/2007/opf/" ` +
    'xmlns:dc="http://purl.org/dc/elements/1.1/" version="1.4">' +
    '<hpf:head><opf:metadata><opf:title>t</opf:title></opf:metadata></hpf:head>' +
    '<opf:manifest>' +
    '<opf:item id="header" href="Contents/header.xml" media-type="application/xml"/>' +
    '<opf:item id="section0" href="Contents/section0.xml" media-type="application/xml"/>' +
    '</opf:manifest>' +
    '<opf:spine><opf:itemref idref="section0" linetype="user"/></opf:spine></hpf:package>';

  const headerXml =
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
    `<hh:head xmlns:hh="${NS_HH}" xmlns:hc="${NS_HC}" version="1.4" secCnt="1"><hh:refList>` +
    '</hh:refList></hh:head>';

  const para = (text, pid) =>
    `<hp:p id="${pid}" paraPrIDRef="0" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0">` +
    `<hp:run charPrIDRef="0"><hp:t>${text}</hp:t></hp:run></hp:p>`;

  const sectionXml =
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
    `<hs:sec xmlns:hs="${NS_HS}" xmlns:hp="${NS_HP}" xmlns:hc="${NS_HC}">` +
    paragraphs.map((t, i) => para(t, i)).join('') +
    '</hs:sec>';

  const zip = new JSZip();
  zip.file('mimetype', 'application/hwp+zip', { compression: 'STORE' });
  zip.file('META-INF/container.xml', containerXml);
  zip.file('Contents/content.hpf', contentHpf);
  zip.file('Contents/header.xml', headerXml);
  zip.file('Contents/section0.xml', sectionXml);
  return zip.generateAsync({ type: 'nodebuffer' });
}

test('HWPX 가져오기 → 에디터에 문단 반영', async ({ page }) => {
  await login(page, 'hwp-author@x.com');
  await page.goto('/write/hwp-import-room');

  const buffer = await buildHwpx(['첫 문단입니다', '둘째 문단입니다', '셋째']);
  await page.locator('input[accept=".hwp,.hwpx"]').setInputFiles({
    name: 'manuscript.hwpx',
    mimeType: 'application/hwp+zip',
    buffer,
  });

  const editor = page.locator('.ProseMirror');
  await expect(editor).toContainText('첫 문단입니다');
  await expect(editor).toContainText('둘째 문단입니다');
  await expect(editor).toContainText('셋째');
});

test('손상된 HWP 업로드 → 실패 안내(PDF 변환 유도)', async ({ page }) => {
  await login(page, 'hwp-author@x.com');
  await page.goto('/write/hwp-import-room');

  await page.locator('input[accept=".hwp,.hwpx"]').setInputFiles({
    name: 'broken.hwpx',
    mimeType: 'application/hwp+zip',
    buffer: Buffer.from('not a hwpx'),
  });

  await expect(page.getByText(/가져오기 실패/)).toBeVisible();
  await expect(page.getByText(/PDF/)).toBeVisible();
});
