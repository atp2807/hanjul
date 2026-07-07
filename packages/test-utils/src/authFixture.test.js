import { describe, expect, it } from 'vitest';

import { authFixture } from './authFixture.js';

describe('authFixture', () => {
  it('기본값 — user null·loading false·login/logout 은 호출 가능한 vi.fn', () => {
    const auth = authFixture();
    expect(auth.user).toBeNull();
    expect(auth.loading).toBe(false);
    auth.login('token');
    auth.logout();
    expect(auth.login).toHaveBeenCalledWith('token');
    expect(auth.logout).toHaveBeenCalledTimes(1);
  });

  it('overrides 가 기본값을 덮어쓴다', () => {
    const auth = authFixture({ user: { id: 'u1' }, loading: true });
    expect(auth.user).toEqual({ id: 'u1' });
    expect(auth.loading).toBe(true);
    // 명시적으로 덮지 않은 필드는 기본 vi.fn 유지
    expect(typeof auth.logout).toBe('function');
  });
});
