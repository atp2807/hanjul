// HWP(한글) 가져오기 어댑터 — DOCX/EPUB와 달리 바이너리 파싱은 서버(rhwp)에서 한다.
// 업로드 → 서버가 중립 블록 JSON({blocks:[...]})을 그대로 반환 → 다른 어댑터와 동일하게 소비.
import { apiClient } from '../../services/api/api_client';

export async function hwpToNeutral(file) {
  const fd = new FormData();
  fd.append('file', file);
  return apiClient.upload('/import/hwp-parse', fd);
}
