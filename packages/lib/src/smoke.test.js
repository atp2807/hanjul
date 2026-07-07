// 인프라 스모크 — vitest+jsdom 셋업이 이 패키지에서 실제로 도는지만 증명한다.
// 본 테스트 스위트(apiClient/createAuthContext 등)는 W4 에서 추가.
import { describe, expect, it } from 'vitest';

import { createApiClient } from './apiClient.js';

describe('@hanjul/lib 인프라 스모크', () => {
  it('createApiClient 는 함수다', () => {
    expect(typeof createApiClient).toBe('function');
  });
});
