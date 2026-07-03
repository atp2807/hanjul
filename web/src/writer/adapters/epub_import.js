// EPUB 가져오기 어댑터 — jszip(압축해제) + OPF(spine 순서) + XHTML→중립(공용 htmlToNeutral).
// DOCX 어댑터와 대칭. 어댑터 레이어라 DOM(DOMParser) 사용 OK.
// 잘못된 EPUB 은 조용히 빈 결과를 내지 않고 명확한(한국어) Error 를 던져 호출부가 사용자에게 보여준다.
import JSZip from 'jszip';

import { htmlToNeutral } from './html_to_neutral';

// OPF 디렉토리 기준 상대 href → zip 내부 절대경로. `.`/`..` 정규화.
function resolvePath(baseDir, href) {
  const decoded = decodeURIComponent(href.split('#')[0].split('?')[0]);
  const segments = (baseDir ? baseDir.split('/') : []).concat(decoded.split('/'));
  const out = [];
  for (const seg of segments) {
    if (seg === '' || seg === '.') continue;
    if (seg === '..') out.pop();
    else out.push(seg);
  }
  return out.join('/');
}

function dirOf(path) {
  const i = path.lastIndexOf('/');
  return i === -1 ? '' : path.slice(0, i);
}

// zip 에서 파일 텍스트 읽기 (없으면 에러). EPUB 경로는 대소문자 정확해야 함.
async function readText(zip, path, label) {
  const entry = zip.file(path);
  if (!entry) throw new Error(`${label}을(를) 찾을 수 없어요 (${path}).`);
  return entry.async('string');
}

function parseXml(text, label) {
  const doc = new DOMParser().parseFromString(text, 'application/xml');
  if (doc.querySelector('parsererror')) throw new Error(`${label}을(를) 해석할 수 없어요.`);
  return doc;
}

export async function epubToNeutral(arrayBuffer) {
  // 1. 압축 해제 (zip 아니면 여기서 실패)
  let zip;
  try {
    zip = await JSZip.loadAsync(arrayBuffer);
  } catch {
    throw new Error('EPUB 파일을 읽을 수 없어요. (올바른 EPUB/ZIP 이 아니에요)');
  }

  // 2. container.xml → OPF 경로
  const containerXml = await readText(zip, 'META-INF/container.xml', 'EPUB 컨테이너(container.xml)');
  const container = parseXml(containerXml, 'EPUB 컨테이너');
  const rootfile = container.querySelector('rootfile');
  const opfPath = rootfile?.getAttribute('full-path');
  if (!opfPath) throw new Error('지원하지 않는 EPUB 구조예요. (OPF 경로를 찾을 수 없어요)');

  // 3. OPF → manifest(id→href) + spine 순서(idref, linear="no" 제외)
  const opfXml = await readText(zip, opfPath, 'EPUB 목록(OPF)');
  const opf = parseXml(opfXml, 'EPUB 목록(OPF)');
  const opfDir = dirOf(opfPath);

  const manifest = {};
  opf.querySelectorAll('manifest > item').forEach((item) => {
    const id = item.getAttribute('id');
    const href = item.getAttribute('href');
    if (id && href) manifest[id] = resolvePath(opfDir, href);
  });

  const spine = [...opf.querySelectorAll('spine > itemref')]
    .filter((ref) => ref.getAttribute('linear') !== 'no')
    .map((ref) => ref.getAttribute('idref'))
    .filter((idref) => idref && manifest[idref]);

  if (!spine.length) throw new Error('지원하지 않는 EPUB 구조예요. (읽을 본문(spine)이 없어요)');

  // 4~6. spine 순서대로 XHTML → 중립 블록, 챕터 제목 보강, 이어붙임
  const blocks = [];
  let chapterNo = 0;
  for (const idref of spine) {
    chapterNo += 1;
    const path = manifest[idref];
    const entry = zip.file(path);
    if (!entry) continue; // 매니페스트에 있으나 실제 파일 없으면 건너뜀
    const xhtml = await entry.async('string');
    const { blocks: chBlocks } = htmlToNeutral(xhtml);
    if (!chBlocks.length) continue; // 빈 스파인 건너뜀

    // 챕터 제목: 첫 블록이 이미 헤딩이면 그대로, 아니면 <title> 또는 "N장"을 h1 로 앞에 붙임
    if (chBlocks[0].type[0] !== 'h') {
      const titleEl = new DOMParser().parseFromString(xhtml, 'text/html').querySelector('head > title');
      const title = titleEl?.textContent.trim();
      chBlocks.unshift({ type: 'h1', spans: [{ text: title || `${chapterNo}장`, marks: [] }] });
    }
    blocks.push(...chBlocks);
  }

  // 내용이 전부 비어 있으면 빈 결과 반환(호출부가 "가져올 내용이 없어요" 안내) — DOCX 경로와 대칭.
  return { blocks };
}
