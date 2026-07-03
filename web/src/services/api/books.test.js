import { describe, expect, it, vi } from 'vitest';

import { apiClient } from './api_client';
import { flattenBlocks, getBookContent, getStoreDetail, listStore } from './books';

vi.mock('./api_client', () => ({
  apiClient: { get: vi.fn(), post: vi.fn(), put: vi.fn(), del: vi.fn() },
}));

describe('services/api/books', () => {
  it('listStore → 파라미터 없으면 쿼리스트링 없이', () => {
    listStore();
    expect(apiClient.get).toHaveBeenCalledWith('/store/books');
  });

  it('listStore → q·kind·category 모두 반영', () => {
    listStore('한 줄', 'BOOK', '에세이');
    expect(apiClient.get).toHaveBeenCalledWith('/store/books?q=%ED%95%9C+%EC%A4%84&kind=BOOK&category=%EC%97%90%EC%84%B8%EC%9D%B4');
  });

  it('listStore → 일부만 지정해도 나머지는 빠짐', () => {
    listStore(undefined, undefined, '소설');
    expect(apiClient.get).toHaveBeenCalledWith('/store/books?category=%EC%86%8C%EC%84%A4');
  });

  it('getStoreDetail → GET /store/books/:id', () => {
    getStoreDetail('b1');
    expect(apiClient.get).toHaveBeenCalledWith('/store/books/b1');
  });

  it('getBookContent → GET /books/:id/content', () => {
    getBookContent('b1');
    expect(apiClient.get).toHaveBeenCalledWith('/books/b1/content');
  });

  it('flattenBlocks → 모든 장의 블록을 이어붙임', () => {
    const content = {
      chapters: [
        { blocks: [{ id: 'b1', blockType: 'h1', html: '<h1>1장</h1>' }] },
        { blocks: [{ id: 'b2', blockType: 'p', html: '<p>본문</p>' }, { id: 'b3', blockType: 'p', html: '<p>본문2</p>' }] },
      ],
    };
    expect(flattenBlocks(content)).toEqual([
      { id: 'b1', type: 'h1', html: '<h1>1장</h1>' },
      { id: 'b2', type: 'p', html: '<p>본문</p>' },
      { id: 'b3', type: 'p', html: '<p>본문2</p>' },
    ]);
  });

  it('flattenBlocks → 장이 없으면 빈 배열', () => {
    expect(flattenBlocks({ chapters: [] })).toEqual([]);
  });
});
