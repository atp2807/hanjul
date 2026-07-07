import { apiClient } from './api_client';

// 스토어 — 출판된 책 목록 (검색 + 카테고리)
export function listStore(q, kind, category) {
  const params = new URLSearchParams();
  if (q) params.set('q', q);
  if (kind) params.set('kind', kind);
  if (category) params.set('category', category);
  const qs = params.toString();
  return apiClient.get(`/store/books${qs ? `?${qs}` : ''}`);
}

// 스토어 — 책 상세 (출판본만)
export function getStoreDetail(bookId) {
  return apiClient.get(`/store/books/${bookId}`);
}

// 정본 — 리더용 본문 (장/블록)
export function getBookContent(bookId) {
  return apiClient.get(`/books/${bookId}/content`);
}

function escapeHtml(s) {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

// 정본 응답을 리더가 쓰는 평면 블록 리스트로 (모든 장의 블록 이어붙임)
// 장 제목(chapters[].title)은 출판 시 본문에서 분리돼 메타로만 남기 때문에,
// 여기서 H1 블록으로 되살려 넣어야 독자가 장 경계를 볼 수 있다(Reader의 목차도 이 H1을 스캔해 만든다).
export function flattenBlocks(content) {
  return content.chapters.flatMap((ch, i) => {
    const body = ch.blocks.map((b) => ({ id: b.id, type: b.blockType, html: b.html }));
    if (!ch.title) return body;
    return [{ id: `ch-title-${i}`, type: 'H1', html: `<h1>${escapeHtml(ch.title)}</h1>` }, ...body];
  });
}
