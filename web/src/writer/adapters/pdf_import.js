// PDF 가져오기 어댑터 — 서버 파싱(pymupdf) 후 중립 doc 수신.
// DOCX/EPUB 은 브라우저에서 파싱하지만 PDF 는 서버(POST /import/pdf-parse)가 텍스트·
// 서식을 추출한다. 결과 중립 doc 은 neutralToPmDoc 로 에디터에 적재되고, 출판 시 정본까지
// 같은 경로. 업로드 패턴은 studio.js uploadCover 참고.
import { apiClient } from '../../services/api/api_client';

// 브라우저 File → 중립 doc ({ blocks: [{ type, spans:[{text,marks}] }] })
export async function pdfToNeutral(file) {
  const fd = new FormData();
  fd.append('file', file);
  return apiClient.upload('/import/pdf-parse', fd);
}
