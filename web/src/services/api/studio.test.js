import { describe, expect, it, vi } from 'vitest';

import { apiClient } from './api_client';
import {
  createBook,
  deleteBook,
  distributeBook,
  downloadEpub,
  downloadOnix,
  generateCover,
  getDistributions,
  getMyBooks,
  getSales,
  importText,
  publishBook,
  publishNow,
  schedulePublish,
  setBookContent,
  setBookPrice,
  setDiscount,
  setIsbn,
  setPreviewLimit,
  submitBook,
  suggestBlurb,
  unpublishBook,
  updateMeta,
  uploadCover,
} from './studio';

vi.mock('./api_client', () => ({
  apiClient: { get: vi.fn(), post: vi.fn(), put: vi.fn(), del: vi.fn(), upload: vi.fn(), download: vi.fn() },
}));

describe('services/api/studio', () => {
  it('getMyBooks → GET /me/books', () => {
    getMyBooks();
    expect(apiClient.get).toHaveBeenCalledWith('/me/books');
  });

  it('getSales → GET /me/sales', () => {
    getSales();
    expect(apiClient.get).toHaveBeenCalledWith('/me/sales');
  });

  it('createBook → kind 기본값 BOOK', () => {
    createBook('새 책');
    expect(apiClient.post).toHaveBeenCalledWith('/books', { title: '새 책', kind: 'BOOK' });
  });

  it('createBook → kind 지정 시 그대로', () => {
    createBook('연재작', 'WEBNOVEL');
    expect(apiClient.post).toHaveBeenCalledWith('/books', { title: '연재작', kind: 'WEBNOVEL' });
  });

  it('importText → POST /books/:id/import', () => {
    importText('b1', '본문', '1장');
    expect(apiClient.post).toHaveBeenCalledWith('/books/b1/import', { rawText: '본문', chapterTitle: '1장' });
  });

  it('setBookPrice → PUT /books/:id/price', () => {
    setBookPrice('b1', 9900);
    expect(apiClient.put).toHaveBeenCalledWith('/books/b1/price', { amount: 9900 });
  });

  it('setDiscount → PUT /books/:id/discount', () => {
    setDiscount('b1', 5000, '2026-08-01T00:00:00.000Z');
    expect(apiClient.put).toHaveBeenCalledWith('/books/b1/discount', { amount: 5000, until: '2026-08-01T00:00:00.000Z' });
  });

  it('submitBook → POST /books/:id/submit', () => {
    submitBook('b1');
    expect(apiClient.post).toHaveBeenCalledWith('/books/b1/submit');
  });

  it('publishBook → POST /books/:id/publish', () => {
    publishBook('b1');
    expect(apiClient.post).toHaveBeenCalledWith('/books/b1/publish');
  });

  it('publishNow → POST /books/:id/publish-now', () => {
    publishNow('b1');
    expect(apiClient.post).toHaveBeenCalledWith('/books/b1/publish-now');
  });

  it('deleteBook → DELETE /books/:id', () => {
    deleteBook('b1');
    expect(apiClient.del).toHaveBeenCalledWith('/books/b1');
  });

  it('unpublishBook → POST /books/:id/unpublish', () => {
    unpublishBook('b1');
    expect(apiClient.post).toHaveBeenCalledWith('/books/b1/unpublish');
  });

  it('setPreviewLimit → PUT /books/:id/preview-limit', () => {
    setPreviewLimit('b1', 3);
    expect(apiClient.put).toHaveBeenCalledWith('/books/b1/preview-limit', { limit: 3 });
  });

  it('schedulePublish → POST /books/:id/schedule', () => {
    schedulePublish('b1', '2026-08-01T00:00:00.000Z');
    expect(apiClient.post).toHaveBeenCalledWith('/books/b1/schedule', { publishAt: '2026-08-01T00:00:00.000Z' });
  });

  it('setIsbn → PUT /books/:id/isbn', () => {
    setIsbn('b1', '9788912345678');
    expect(apiClient.put).toHaveBeenCalledWith('/books/b1/isbn', { isbn: '9788912345678' });
  });

  it('updateMeta → PUT /books/:id/meta', () => {
    updateMeta('b1', { subtitle: '부제', description: '소개', category: '소설' });
    expect(apiClient.put).toHaveBeenCalledWith('/books/b1/meta', { subtitle: '부제', description: '소개', category: '소설' });
  });

  it('suggestBlurb → GET /books/:id/suggest-blurb', () => {
    suggestBlurb('b1');
    expect(apiClient.get).toHaveBeenCalledWith('/books/b1/suggest-blurb');
  });

  it('generateCover → POST /books/:id/cover', () => {
    generateCover('b1', '잔잔한 표지');
    expect(apiClient.post).toHaveBeenCalledWith('/books/b1/cover', { prompt: '잔잔한 표지' });
  });

  it('uploadCover → multipart 파일 업로드', () => {
    const file = new File(['x'], 'cover.png', { type: 'image/png' });
    uploadCover('b1', file);
    // eslint-disable-next-line vitest/valid-expect -- @vitest/eslint-plugin 오탐: expect.any()가 중첩 인자로 쓰일 때 modifier로 오인
    expect(apiClient.upload).toHaveBeenCalledWith('/books/b1/cover/upload', expect.any(FormData));
    const fd = apiClient.upload.mock.calls[0][1];
    expect(fd.get('file')).toBe(file);
  });

  it('setBookContent → PUT /books/:id/content', () => {
    const chapters = [{ title: '1장', blocks: [{ type: 'p', html: '<p>x</p>' }] }];
    setBookContent('b1', chapters);
    expect(apiClient.put).toHaveBeenCalledWith('/books/b1/content', { chapters });
  });

  it('distributeBook → POST /books/:id/distribute', () => {
    distributeBook('b1', 'KYOBO');
    expect(apiClient.post).toHaveBeenCalledWith('/books/b1/distribute', { channel: 'KYOBO' });
  });

  it('getDistributions → GET /books/:id/distributions', () => {
    getDistributions('b1');
    expect(apiClient.get).toHaveBeenCalledWith('/books/b1/distributions');
  });

  it('downloadEpub → 파일명 지정해 다운로드', () => {
    downloadEpub('b1');
    expect(apiClient.download).toHaveBeenCalledWith('/books/b1/epub', 'b1.epub');
  });

  it('downloadOnix → 파일명 지정해 다운로드', () => {
    downloadOnix('b1');
    expect(apiClient.download).toHaveBeenCalledWith('/books/b1/onix', 'b1.onix.xml');
  });
});
