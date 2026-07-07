// createApiClient() — web·potato 공용 API 클라이언트 팩토리 실코드 테스트.
// 지금까지 모든 소비처가 apiClient 모듈 자체를 vi.mock 해버려서 이 팩토리의 실제
// fetch 호출 조립·에러 파싱·토큰 저장 로직은 한 번도 실행된 적이 없었다.
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { createApiClient } from './apiClient.js';

const TOKEN_KEY = 'test_token';

describe('createApiClient', () => {
  let client;

  beforeEach(() => {
    localStorage.clear();
    global.fetch = vi.fn();
    client = createApiClient(TOKEN_KEY);
  });

  describe('get/post/put/del — URL·헤더 조립', () => {
    it('get() — /api 접두 + Content-Type, 토큰 없으면 Authorization 없음', async () => {
      fetch.mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ items: [] }) });
      await client.get('/books');
      const [url, opts] = fetch.mock.calls[0];
      expect(url).toBe('/api/books');
      expect(opts.headers['Content-Type']).toBe('application/json');
      expect(opts.headers.Authorization).toBeUndefined();
    });

    it('토큰 있으면 Authorization: Bearer 자동 첨부', async () => {
      client.setToken('tok-123');
      fetch.mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({}) });
      await client.get('/me');
      const [, opts] = fetch.mock.calls[0];
      expect(opts.headers.Authorization).toBe('Bearer tok-123');
    });

    it('post(path, body) — method POST + JSON.stringify(body)', async () => {
      fetch.mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ id: 1 }) });
      await client.post('/books', { title: '제목' });
      const [url, opts] = fetch.mock.calls[0];
      expect(url).toBe('/api/books');
      expect(opts.method).toBe('POST');
      expect(opts.body).toBe(JSON.stringify({ title: '제목' }));
    });

    it('post(path) — body 없으면 undefined로 전송(빈 문자열 JSON 아님)', async () => {
      fetch.mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({}) });
      await client.post('/books/1/publish');
      const [, opts] = fetch.mock.calls[0];
      expect(opts.body).toBeUndefined();
    });

    it('put(path, body) — method PUT', async () => {
      fetch.mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({}) });
      await client.put('/books/1', { title: '수정' });
      const [url, opts] = fetch.mock.calls[0];
      expect(url).toBe('/api/books/1');
      expect(opts.method).toBe('PUT');
      expect(opts.body).toBe(JSON.stringify({ title: '수정' }));
    });

    it('del(path) — method DELETE', async () => {
      fetch.mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({}) });
      await client.del('/books/1');
      const [url, opts] = fetch.mock.calls[0];
      expect(url).toBe('/api/books/1');
      expect(opts.method).toBe('DELETE');
    });
  });

  describe('에러 파싱 (toError)', () => {
    it('401 — 문자열 detail이면 err.status/err.detail/message 전부 detail', async () => {
      fetch.mockResolvedValueOnce({
        ok: false,
        status: 401,
        json: async () => ({ detail: '로그인이 필요합니다' }),
      });
      await expect(client.get('/me')).rejects.toMatchObject({
        status: 401,
        detail: '로그인이 필요합니다',
        message: '로그인이 필요합니다',
      });
    });

    it('422 — detail이 배열(FastAPI validation)이면 detail=null, message는 status:path 폴백', async () => {
      fetch.mockResolvedValueOnce({
        ok: false,
        status: 422,
        json: async () => ({ detail: [{ loc: ['body', 'title'], msg: 'field required' }] }),
      });
      await expect(client.post('/books', {})).rejects.toMatchObject({
        status: 422,
        detail: null,
        message: 'API 422: /books',
      });
    });

    it('본문이 JSON이 아니면(res.json() throw) detail=null, message는 status:path 폴백', async () => {
      fetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: async () => { throw new Error('not json'); },
      });
      await expect(client.get('/boom')).rejects.toMatchObject({
        status: 500,
        detail: null,
        message: 'API 500: /boom',
      });
    });
  });

  describe('204 No Content', () => {
    it('204 응답이면 res.json()을 호출하지 않고 null을 반환한다', async () => {
      const json = vi.fn();
      fetch.mockResolvedValueOnce({ ok: true, status: 204, json });
      const result = await client.del('/books/1');
      expect(result).toBeNull();
      expect(json).not.toHaveBeenCalled();
    });
  });

  describe('download', () => {
    it('성공 — Content-Disposition 헤더에서 파일명을 파싱해 a.download에 쓴다', async () => {
      const blob = new Blob(['data']);
      fetch.mockResolvedValueOnce({
        ok: true,
        headers: { get: (k) => (k === 'Content-Disposition' ? 'attachment; filename="report.epub"' : null) },
        blob: async () => blob,
      });
      vi.stubGlobal('URL', { createObjectURL: vi.fn(() => 'blob:xyz'), revokeObjectURL: vi.fn() });
      let capturedName;
      vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(function mockClick() {
        capturedName = this.download;
      });

      await client.download('/books/1/epub', 'fallback.epub');

      expect(capturedName).toBe('report.epub');
      expect(URL.createObjectURL).toHaveBeenCalledWith(blob);
      expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:xyz');
    });

    it('Content-Disposition 헤더가 없으면 fallbackName을 쓴다', async () => {
      fetch.mockResolvedValueOnce({
        ok: true,
        headers: { get: () => null },
        blob: async () => new Blob(['x']),
      });
      vi.stubGlobal('URL', { createObjectURL: () => 'blob:x', revokeObjectURL: vi.fn() });
      let capturedName;
      vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(function mockClick() {
        capturedName = this.download;
      });

      await client.download('/books/1/onix', 'default.onix.xml');

      expect(capturedName).toBe('default.onix.xml');
    });

    it('실패 응답이면 get과 동일하게 toError를 던진다', async () => {
      fetch.mockResolvedValueOnce({ ok: false, status: 403, json: async () => ({ detail: '권한 없음' }) });
      await expect(client.download('/books/1/epub', 'x.epub')).rejects.toMatchObject({
        status: 403,
        detail: '권한 없음',
      });
    });
  });

  describe('upload', () => {
    it('FormData를 그대로 POST하고 Content-Type은 지정하지 않는다(브라우저 자동 boundary)', async () => {
      client.setToken('tok-abc');
      const fd = new FormData();
      fetch.mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ url: 'x.png' }) });

      const result = await client.upload('/covers', fd);

      const [url, opts] = fetch.mock.calls[0];
      expect(url).toBe('/api/covers');
      expect(opts.method).toBe('POST');
      expect(opts.body).toBe(fd);
      expect(opts.headers['Content-Type']).toBeUndefined();
      expect(opts.headers.Authorization).toBe('Bearer tok-abc');
      expect(result).toEqual({ url: 'x.png' });
    });
  });

  describe('토큰 저장 (getToken/setToken)', () => {
    it('setToken(token) — localStorage에 저장되고 getToken()으로 읽힌다', () => {
      client.setToken('abc');
      expect(localStorage.getItem(TOKEN_KEY)).toBe('abc');
      expect(client.getToken()).toBe('abc');
    });

    it('setToken(null) — localStorage에서 제거한다', () => {
      localStorage.setItem(TOKEN_KEY, 'abc');
      client.setToken(null);
      expect(localStorage.getItem(TOKEN_KEY)).toBeNull();
      expect(client.getToken()).toBeNull();
    });
  });
});
