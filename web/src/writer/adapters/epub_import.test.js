import JSZip from 'jszip';
import { describe, expect, it } from 'vitest';

import { epubToNeutral } from './epub_import';

// 테스트 안에서 최소 EPUB 을 직접 구성(디스크 픽스처 불필요).
// chapters: [{ id, file, title?, body, linear? }], opfDir: OPF 가 놓일 디렉토리.
async function makeEpub(chapters, opfDir = 'OEBPS') {
  const zip = new JSZip();
  zip.file('mimetype', 'application/epub+zip'); // 관례상 첫 항목(파서는 요구 안 함)
  const opfPath = opfDir ? `${opfDir}/content.opf` : 'content.opf';
  zip.file(
    'META-INF/container.xml',
    `<?xml version="1.0"?>
     <container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
       <rootfiles><rootfile full-path="${opfPath}" media-type="application/oebps-package+xml"/></rootfiles>
     </container>`,
  );

  const manifestItems = chapters
    .map((c) => `<item id="${c.id}" href="${c.file}" media-type="application/xhtml+xml"/>`)
    .join('\n');
  const spineItems = chapters
    .map((c) => `<itemref idref="${c.id}"${c.linear === false ? ' linear="no"' : ''}/>`)
    .join('\n');
  zip.file(
    opfPath,
    `<?xml version="1.0" encoding="utf-8"?>
     <package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="uid">
       <metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>테스트책</dc:title></metadata>
       <manifest>${manifestItems}</manifest>
       <spine>${spineItems}</spine>
     </package>`,
  );

  for (const c of chapters) {
    const full = opfDir ? `${opfDir}/${c.file}` : c.file;
    zip.file(
      full,
      `<?xml version="1.0" encoding="utf-8"?>
       <!DOCTYPE html>
       <html xmlns="http://www.w3.org/1999/xhtml">
         <head><title>${c.title ?? ''}</title></head>
         <body>${c.body}</body>
       </html>`,
    );
  }
  return zip.generateAsync({ type: 'arraybuffer' });
}

describe('epubToNeutral', () => {
  it('(a) 단일 챕터 → 문단/제목 블록 정상 변환', async () => {
    const buf = await makeEpub([
      { id: 'c1', file: 'ch1.xhtml', body: '<h1>1장 도입</h1><p>첫 문단 <strong>굵게</strong> <em>기울임</em></p>' },
    ]);
    const { blocks } = await epubToNeutral(buf);

    expect(blocks[0]).toEqual({ type: 'h1', spans: [{ text: '1장 도입', marks: [] }] });
    expect(blocks[1].type).toBe('p');
    expect(blocks[1].spans).toEqual([
      { text: '첫 문단 ', marks: [] },
      { text: '굵게', marks: ['strong'] },
      { text: ' ', marks: [] },
      { text: '기울임', marks: ['em'] },
    ]);
  });

  it('(b) 여러 챕터 → spine 순서대로 이어붙고 챕터별 제목이 h1 로', async () => {
    const buf = await makeEpub([
      { id: 'c1', file: 'ch1.xhtml', body: '<h1>1장</h1><p>가나다</p>' }, // 이미 헤딩으로 시작 → 그대로
      { id: 'c2', file: 'ch2.xhtml', title: '둘째 장', body: '<p>라마바</p>' }, // 헤딩 없음 → <title> 을 h1 로
      { id: 'c3', file: 'ch3.xhtml', body: '<p>사아자</p>' }, // 헤딩·title 모두 없음 → "N장"
    ]);
    const { blocks } = await epubToNeutral(buf);

    const headings = blocks.filter((b) => b.type === 'h1').map((b) => b.spans[0].text);
    expect(headings).toEqual(['1장', '둘째 장', '3장']);

    // spine 순서 보존: 본문 텍스트가 순서대로
    const paras = blocks.filter((b) => b.type === 'p').map((b) => b.spans[0].text);
    expect(paras).toEqual(['가나다', '라마바', '사아자']);
  });

  it('linear="no" 스파인 항목은 건너뜀', async () => {
    const buf = await makeEpub([
      { id: 'c1', file: 'ch1.xhtml', body: '<h1>본문</h1><p>포함됨</p>' },
      { id: 'nav', file: 'nav.xhtml', linear: false, body: '<h1>표지</h1><p>제외됨</p>' },
    ]);
    const { blocks } = await epubToNeutral(buf);
    const texts = blocks.flatMap((b) => b.spans?.map((s) => s.text) ?? []);
    expect(texts).toContain('포함됨');
    expect(texts).not.toContain('제외됨');
  });

  it('OPF 가 하위 디렉토리에 있어도 href 를 상대경로로 resolve', async () => {
    const buf = await makeEpub([
      { id: 'c1', file: 'text/ch1.xhtml', body: '<h1>깊은 경로</h1><p>읽힘</p>' },
    ], 'OEBPS');
    const { blocks } = await epubToNeutral(buf);
    expect(blocks[0].spans[0].text).toBe('깊은 경로');
    expect(blocks[1].spans[0].text).toBe('읽힘');
  });

  it('(c) EPUB(zip) 이 아니면 명확한 에러', async () => {
    const notZip = new TextEncoder().encode('이건 zip 이 아니에요').buffer;
    await expect(epubToNeutral(notZip)).rejects.toThrow(/EPUB 파일을 읽을 수 없어요/);
  });

  it('container.xml 없으면 명확한 에러', async () => {
    const zip = new JSZip();
    zip.file('random.txt', 'hello');
    const buf = await zip.generateAsync({ type: 'arraybuffer' });
    await expect(epubToNeutral(buf)).rejects.toThrow(/container\.xml/);
  });

  it('spine 이 비면 명확한 에러', async () => {
    const buf = await makeEpub([]); // manifest·spine 모두 빔
    await expect(epubToNeutral(buf)).rejects.toThrow(/지원하지 않는 EPUB 구조/);
  });
});
