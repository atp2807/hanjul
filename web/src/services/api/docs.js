// 한줄독(juldoc) 문서 API — /api/documents·/api/shares·/api/media.
// juldoc web/core/api.js 의 경로를 이식하되, 인증/베이스는 hanjul 클라이언트를 쓴다
// (juldoc 자체 localStorage/Bearer 관리는 폐기 — api_client 가 hanjul JWT 를 얹는다).
//
// 백엔드 계약(juldoc features/documents·shares·media 이식 예정):
//   GET    /api/documents             → { items, total, page, page_size } (item.mine 로 소유 표시)
//   POST   /api/documents/upload      (multipart file) → { id, title, format }
//   POST   /api/documents             { title } → { id, title, format }
//   GET    /api/documents/{id}/html   → 정본 HTML (text/html)
//   PUT    /api/documents/{id}/html   { html } → DocumentResponse
//   POST   /api/media                 (multipart file) → 백엔드 원본은 camelCase MediaResponse
//                                        { url, displayUrl, thumbUrl, bytes, contentType, width, height }
//                                        (url 전부 `/media/{key}`). uploadMedia() 가 juldoc 코어 계약
//                                        (snake_case: url/display_url/thumb_url)으로 매핑해 반환한다.
//   POST   /api/documents/{id}/shares { capability } → 201 ShareResponse
//   GET    /api/documents/{id}/shares → { items, total, page, page_size }
//   DELETE /api/shares/{share_id}     → 204 (멱등 회수)
//   GET    /api/shares/{token}        → { title, capability }
//   GET    /api/shares/{token}/html   → 정본 HTML (text/html)
//   PUT    /api/shares/{token}/html   { html } → 204 (EDIT 만)
//   GET    /api/documents/{id}/export/{epub|docx}   → 첨부 다운로드 (소유자만 — 인증 필요, exportEpub/exportDocx)
//   GET    /api/shares/{token}/export/{epub|docx}   → 첨부 다운로드 (EXPORT 권한, 토큰이 자격 — URL 그대로)
import { apiClient, getToken, apiBase } from './api_client';

// 비-JSON(text/html) 응답 전용 fetch — apiClient.get 은 res.json() 이라 여기선 못 쓴다.
// hanjul JWT(getToken)를 얹고, 실패 시 err.status 를 담아 던진다(공개 페이지가 404/403 분기).
async function fetchText(path) {
  const token = getToken();
  const res = await fetch(`${apiBase}/api${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) {
    const err = new Error(`${res.status} ${res.statusText}`);
    err.status = res.status;
    throw err;
  }
  return res.text();
}

// ── 문서 CRUD / 업로드 ─────────────────────────────────────────

// 문서 목록(페이지네이션). item.mine = 로그인 소유 여부.
export function listDocuments({ page = 1, pageSize = 20 } = {}) {
  const qs = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
  return apiClient.get(`/documents?${qs}`);
}

// 파일 업로드 → 새 문서. multipart(field=file).
export function uploadDocument(file) {
  const form = new FormData();
  form.append('file', file);
  return apiClient.upload('/documents/upload', form);
}

// 빈 문서 생성.
export function createDocument(title) {
  return apiClient.post('/documents', { title });
}

// 단일 문서 메타(제목·format·mine). 본문 HTML 은 별도(getDocumentHtml).
export function getDocument(id) {
  return apiClient.get(`/documents/${encodeURIComponent(id)}`);
}

// 문서 정본 HTML (리더/에디터 로드).
export function getDocumentHtml(id) {
  return fetchText(`/documents/${encodeURIComponent(id)}/html`);
}

// 문서 정본 HTML 저장(에디터 save). 반환 DocumentResponse.
export function saveDocumentHtml(id, html) {
  return apiClient.put(`/documents/${encodeURIComponent(id)}/html`, { html });
}

// 문서 삭제.
export function deleteDocument(id) {
  return apiClient.del(`/documents/${encodeURIComponent(id)}`);
}

// 이미지 업로드 → variant url(전부 `/media/{key}` 정본 상대경로). multipart(field=file).
// 서버가 최대 변 4096px 초과를 거부 → 에디터가 업로드 전 클라 축소로 방어.
// 백엔드 응답은 camelCase(MediaResponse) 지만 juldoc 에디터 코어(packages/doc editor.js)는
// snake_case 계약(display_url 우선, url 폴백)을 그대로 기대한다 — 코어는 이식 verbatim 이라
// 건드리지 않고, 여기(경계 어댑터)서 매핑해 반환한다.
export async function uploadMedia(file) {
  const form = new FormData();
  form.append('file', file);
  const res = await apiClient.upload('/media', form);
  return {
    url: res.url,
    display_url: res.displayUrl,
    thumb_url: res.thumbUrl,
    bytes: res.bytes,
    content_type: res.contentType,
    width: res.width,
    height: res.height,
  };
}

// ── 공유 링크 ──────────────────────────────────────────────────

// 공유 링크 발급. capability = 'view' | 'edit' | 'export'.
export function createShare(docId, capability) {
  return apiClient.post(`/documents/${encodeURIComponent(docId)}/shares`, { capability });
}

// 문서의 공유 링크 목록(회수분 포함).
export function listShares(docId, { page = 1, pageSize = 50 } = {}) {
  const qs = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
  return apiClient.get(`/documents/${encodeURIComponent(docId)}/shares?${qs}`);
}

// 공유 링크 회수(멱등 — 이미 회수됐어도 성공, 204).
export function revokeShare(shareId) {
  return apiClient.del(`/shares/${encodeURIComponent(shareId)}`);
}

// 공개 링크 메타(문서 제목 + 권한). 404 → err.status === 404 (회수/부재).
export function getShareMeta(token) {
  return apiClient.get(`/shares/${encodeURIComponent(token)}`);
}

// 공개 링크 정본 HTML.
export function getShareHtml(token) {
  return fetchText(`/shares/${encodeURIComponent(token)}/html`);
}

// 공개 링크 저장(EDIT 권한만, 204). 403 → err.status === 403.
export function saveShareHtml(token, html) {
  return apiClient.put(`/shares/${encodeURIComponent(token)}/html`, { html });
}

// ── 수출(내 문서) ──────────────────────────────────────────────
// 소유 문서 수출은 ensure_can_modify(인증) 대상 — <a href> 로는 Authorization 을 못 실어
// mine 문서가 403 나던 결함. apiClient.download 로 Bearer 를 태워 blob 다운로드한다.
export function exportEpub(id, title) {
  return apiClient.download(`/documents/${encodeURIComponent(id)}/export/epub`, `${title || id}.epub`);
}
export function exportDocx(id, title) {
  return apiClient.download(`/documents/${encodeURIComponent(id)}/export/docx`, `${title || id}.docx`);
}

// ── 수출 URL(공유 링크, juldoc 동일: <a href download> 직접 다운로드) ────
// 토큰이 곧 접근 자격이라 인증 불필요. 프론트(www)·API(api) 오리진이 달라 절대경로(apiBase 접두)로 만든다.

export function shareExportEpubUrl(token) {
  return `${apiBase}/api/shares/${encodeURIComponent(token)}/export/epub`;
}
export function shareExportDocxUrl(token) {
  return `${apiBase}/api/shares/${encodeURIComponent(token)}/export/docx`;
}
