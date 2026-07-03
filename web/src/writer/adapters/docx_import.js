// DOCX 가져오기 어댑터 — mammoth(docx→html) + html→중립 doc.
// html→중립 변환은 EPUB 가져오기와 공유(html_to_neutral.js). 결과 중립 doc 은
// neutralToPmDoc 로 에디터에 적재되고, 출판 시 정본까지 같은 경로.
import mammoth from 'mammoth';

import { htmlToNeutral } from './html_to_neutral';

export { htmlToNeutral }; // 하위호환 재수출(기존 import 경로 유지)

// 브라우저: File.arrayBuffer() → 중립 doc
export async function docxToNeutral(arrayBuffer) {
  const { value: html } = await mammoth.convertToHtml({ arrayBuffer });
  return htmlToNeutral(html);
}
