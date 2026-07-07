import { describe, expect, it, vi } from 'vitest';

import { mockApiClient } from '@hanjul/test-utils';
import { apiClient } from './api_client';
import { flattenBlocks, getBookContent, getStoreDetail, listStore } from './books';

vi.mock('./api_client', () => ({
  apiClient: mockApiClient(),
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

  it('flattenBlocks → 장 제목이 있으면 H1 블록으로 되살아나 목차/가독성에 씀', () => {
    const content = {
      chapters: [
        { title: '1장 시작', blocks: [{ id: 'b1', blockType: 'p', html: '<p>본문</p>' }] },
        { title: null, blocks: [{ id: 'b2', blockType: 'p', html: '<p>무제 챕터 본문</p>' }] },
      ],
    };
    expect(flattenBlocks(content)).toEqual([
      { id: 'ch-title-0', type: 'H1', html: '<h1>1장 시작</h1>' },
      { id: 'b1', type: 'p', html: '<p>본문</p>' },
      { id: 'b2', type: 'p', html: '<p>무제 챕터 본문</p>' },
    ]);
  });

  it('flattenBlocks → 장 제목의 특수문자는 이스케이프', () => {
    const content = { chapters: [{ title: '<script> & "장"', blocks: [] }] };
    expect(flattenBlocks(content)).toEqual([
      { id: 'ch-title-0', type: 'H1', html: '<h1>&lt;script&gt; &amp; "장"</h1>' },
    ]);
  });
});
