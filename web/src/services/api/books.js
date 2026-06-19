import { apiClient } from './api_client';

// 스토어 — 출판된 책 목록 (검색 + 카테고리)
export function listStore(q, kind) {
  const params = new URLSearchParams();
  if (q) params.set('q', q);
  if (kind) params.set('kind', kind);
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

// 정본 응답을 리더가 쓰는 평면 블록 리스트로 (모든 장의 블록 이어붙임)
export function flattenBlocks(content) {
  return content.chapters.flatMap((ch) =>
    ch.blocks.map((b) => ({ id: b.id, type: b.blockType, html: b.html })),
  );
}
