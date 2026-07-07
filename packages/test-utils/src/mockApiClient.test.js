import { describe, expect, it, vi } from 'vitest';

import { mockApiClient } from './mockApiClient.js';

describe('mockApiClient', () => {
  it('get/post/put/del/upload/download 6개 전부 독립적인 vi.fn', () => {
    const api = mockApiClient();
    const keys = ['get', 'post', 'put', 'del', 'upload', 'download'];
    keys.forEach((k) => expect(vi.isMockFunction(api[k])).toBe(true));

    api.get.mockResolvedValue({ ok: true });
    expect(api.post).not.toHaveBeenCalled();
    expect(api.get).not.toBe(api.post); // 서로 다른 인스턴스(호출 추적 간섭 없음)
  });
});
