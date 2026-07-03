import { expect, test } from '@playwright/test';
import JSZip from 'jszip';

import { login } from './helpers.js';

// 작가의 "현관문": 한글(HWP/HWPX)로 쓴 원고를 그대로 가져와 편집·출판.
// 파싱은 서버(rhwp)에서 하므로 로그인 필요. 디스크 픽스처 없이 테스트 안에서
// jszip으로 최소 HWPX(OWPML)를 즉석 구성 — backend/tests/fixtures/hwpx_fixture.py의
// build_hwpx()와 동일한 최소 구조(문단 1개, 보통 서식) JS 포팅.
async function makeHwpxBuffer(paragraphs) {
  const NS_HH = 'http://www.hancom.co.kr/hwpml/2011/head';
  const NS_HC = 'http://www.hancom.co.kr/hwpml/2011/core';
  const NS_HS = 'http://www.hancom.co.kr/hwpml/2011/section';
  const NS_HP = 'http://www.hancom.co.kr/hwpml/2011/paragraph';
  const NS_OCF = 'urn:oasis:names:tc:opendocument:xmlns:container';
  const NS_HPF = 'http://www.hancom.co.kr/schema/2011/hpf';

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

  const charPr = (cid) =>
    `<hh:charPr id="${cid}" height="1000" textColor="#000000" shadeColor="none" ` +
    'useFontSpace="0" useKerning="0" symMark="NONE" borderFillIDRef="2">' +
    '<hh:fontRef hangul="0" latin="0" hanja="0" japanese="0" other="0" symbol="0" user="0"/>' +
    '<hh:ratio hangul="100" latin="100" hanja="100" japanese="100" other="100" symbol="100" user="100"/>' +
    '<hh:spacing hangul="0" latin="0" hanja="0" japanese="0" other="0" symbol="0" user="0"/>' +
    '<hh:relSz hangul="100" latin="100" hanja="100" japanese="100" other="100" symbol="100" user="100"/>' +
    '<hh:offset hangul="0" latin="0" hanja="0" japanese="0" other="0" symbol="0" user="0"/></hh:charPr>';

  const headerXml =
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
    `<hh:head xmlns:hh="${NS_HH}" xmlns:hc="${NS_HC}" version="1.4" secCnt="1"><hh:refList>` +
    '<hh:fontfaces itemCnt="1"><hh:fontface lang="HANGUL" fontCnt="1">' +
    '<hh:font id="0" face="함초롬바탕" type="TTF"><hh:typeInfo familyType="FCAT_GOTHIC" ' +
    'weight="0" proportion="0" contrast="0" strokeVariation="0" armStyle="0" letterform="0" ' +
    'midline="0" xHeight="0"/></hh:font></hh:fontface></hh:fontfaces>' +
    `<hh:charProperties itemCnt="1">${charPr(0)}</hh:charProperties>` +
    '<hh:paraProperties itemCnt="1"><hh:paraPr id="0" tabPrIDRef="0" condense="0" ' +
    'fontLineHeight="0" snapToGrid="1" suppressLineNumbers="0" checked="0">' +
    '<hh:align horizontal="JUSTIFY" vertical="BASELINE"/>' +
    '<hh:heading type="NONE" idRef="0" level="0"/>' +
    '<hh:breakSetting breakLatinWord="KEEP_WORD" breakNonLatinWord="KEEP_WORD" ' +
    'widowOrphan="0" keepWithNext="0" keepLines="0" pageBreakBefore="0" lineWrap="BREAK"/>' +
    '<hh:margin><hc:intent value="0" unit="HWPUNIT"/><hc:left value="0" unit="HWPUNIT"/>' +
    '<hc:right value="0" unit="HWPUNIT"/><hc:prev value="0" unit="HWPUNIT"/>' +
    '<hc:next value="0" unit="HWPUNIT"/></hh:margin>' +
    '<hh:lineSpacing type="PERCENT" value="160" unit="HWPUNIT"/>' +
    '<hh:border borderFillIDRef="2" offsetLeft="0" offsetRight="0" offsetTop="0" ' +
    'offsetBottom="0" connect="0" ignoreMargin="0"/></hh:paraPr></hh:paraProperties>' +
    '</hh:refList></hh:head>';

  const para = (text) =>
    `<hp:p id="0" paraPrIDRef="0" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0">` +
    `<hp:run charPrIDRef="0"><hp:t>${text}</hp:t></hp:run></hp:p>`;

  const sectionXml =
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
    `<hs:sec xmlns:hs="${NS_HS}" xmlns:hp="${NS_HP}" xmlns:hc="${NS_HC}">` +
    `${paragraphs.map(para).join('')}</hs:sec>`;

  const versionXml =
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
    '<hv:HCFVersion xmlns:hv="http://www.hancom.co.kr/hwpml/2011/version" ' +
    'tagetApplication="WORDPROCESSOR" major="5" minor="1" micro="1" buildNumber="0" ' +
    'os="1" xmlVersion="1.4" application="Hancom Office Hangul" appVersion="12.0"/>';

  const zip = new JSZip();
  zip.file('mimetype', 'application/hwp+zip', { compression: 'STORE' });
  zip.file('version.xml', versionXml);
  zip.file('META-INF/container.xml', containerXml);
  zip.file('Contents/content.hpf', contentHpf);
  zip.file('Contents/header.xml', headerXml);
  zip.file('Contents/section0.xml', sectionXml);
  return zip.generateAsync({ type: 'nodebuffer' });
}

test('HWP(HWPX) 가져오기 → 서버 파싱 → 에디터 반영', async ({ page }) => {
  await login(page, 'hwp-import-author@x.com', 'HWP작가');
  await page.goto('/write/hwp-import-room');

  const buffer = await makeHwpxBuffer(['첫 문단입니다', '둘째 문단입니다']);
  await page.locator('input[accept=".hwp,.hwpx"]').setInputFiles({
    name: 'sample.hwpx',
    mimeType: 'application/hwp+zip',
    buffer,
  });

  await expect(page.getByText(/HWP \d+개 블록을 가져왔어요/)).toBeVisible();
  const editor = page.locator('.ProseMirror');
  await expect(editor).toContainText('첫 문단입니다');
  await expect(editor).toContainText('둘째 문단입니다');
});

test('HWP 가져오기 — 손상된 파일 → 명확한 실패 안내(422)', async ({ page }) => {
  await login(page, 'hwp-import-bad@x.com', 'HWP작가2');
  await page.goto('/write/hwp-import-bad-room');

  await page.locator('input[accept=".hwp,.hwpx"]').setInputFiles({
    name: 'broken.hwp',
    mimeType: 'application/octet-stream',
    buffer: Buffer.from('이건 HWP가 아니에요'),
  });

  await expect(page.getByText(/가져오기 실패/)).toBeVisible();
});
