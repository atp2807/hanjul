import { apiClient } from './api_client';

// GET /api/books/{id}/content → { id, title, chapters: [{ blocks: [{id, blockType, html}] }] }
export function getBookContent(bookId) {
  return apiClient.get(`/books/${bookId}/content`);
}

// 정본 응답을 리더가 쓰는 평면 블록 리스트로 변환 (모든 장의 블록 이어붙임).
export function flattenBlocks(content) {
  return content.chapters.flatMap((ch) =>
    ch.blocks.map((b) => ({ id: b.id, type: b.blockType, html: b.html })),
  );
}
