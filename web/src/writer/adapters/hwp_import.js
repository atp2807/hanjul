// HWP/HWPX 가져오기 어댑터 — 서버 파싱(hwp-hwpx-parser 는 순수 파이썬).
// DOCX/EPUB 는 클라이언트 파싱이지만 HWP 는 파이썬 라이브러리라 서버에 위임한다.
// 서버가 이미 중립 doc {blocks:[{type:'p',spans:[{text,marks}]}]} 로 돌려주므로
// 그대로 반환한다(에러는 그대로 전파 → 호출부가 `가져오기 실패: ${err.message}` 로 노출).
import { apiClient } from '../../services/api/api_client';

// File → 중립 doc {blocks}. 실패 시 서버 detail(예: PDF 변환 안내)이 그대로 던져진다.
export async function hwpToNeutral(file) {
  const fd = new FormData();
  fd.append('file', file);
  return apiClient.upload('/import/hwp-parse', fd);
}
