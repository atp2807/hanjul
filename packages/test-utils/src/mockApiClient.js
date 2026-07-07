// createApiClient() (packages/lib/src/apiClient.js) 리턴 모양의 목 — get/post/put/del/upload/download
// 전부 vi.fn() 이라 mockResolvedValue/mockRejectedValue(httpError(...)) 로 자유롭게 세팅 가능.
import { vi } from 'vitest';

/**
 * @returns {{ get: Function, post: Function, put: Function, del: Function, upload: Function, download: Function }}
 */
export function mockApiClient() {
  return {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    del: vi.fn(),
    upload: vi.fn(),
    download: vi.fn(),
  };
}
