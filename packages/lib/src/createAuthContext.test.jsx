// createAuthContext() — web(user)/potato(operator) 공용 인증 컨텍스트 팩토리 실코드 테스트.
// 소비처는 전부 AuthContext/auth.jsx 자체를 vi.mock 해버려서 토큰→loadUser→user 배선과
// 실패 시 자동 로그아웃 로직이 실행된 적이 없었다. 아래는 그 배선을 직접 검증한다.
import { act, renderHook, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { createAuthContext } from './createAuthContext.jsx';

function setup({ initialToken = null, loadUser = vi.fn(), userKey } = {}) {
  let stored = initialToken;
  const getToken = vi.fn(() => stored);
  const setToken = vi.fn((t) => { stored = t; });
  const { AuthProvider, useAuthContext } = createAuthContext({ getToken, setToken, loadUser, userKey });
  const { result } = renderHook(() => useAuthContext(), { wrapper: AuthProvider });
  return { result, getToken, setToken, loadUser };
}

describe('createAuthContext', () => {
  it('토큰 없음 — loading false, user null (loadUser 호출 안 함)', () => {
    const loadUser = vi.fn();
    const { result } = setup({ loadUser });
    expect(result.current.loading).toBe(false);
    expect(result.current.user).toBeNull();
    expect(loadUser).not.toHaveBeenCalled();
  });

  it('토큰 있음 — loadUser 성공 시 user에 반영되고 loading이 꺼진다', async () => {
    const loadUser = vi.fn().mockResolvedValue({ id: 1, name: '작가' });
    const { result } = setup({ initialToken: 't1', loadUser });
    expect(result.current.loading).toBe(true); // 초기값: !!getToken()
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.user).toEqual({ id: 1, name: '작가' });
    expect(loadUser).toHaveBeenCalledTimes(1);
  });

  it('토큰 있음 — loadUser 실패(401 등) 시 자동 로그아웃: setToken(null) 호출 + user/token 초기화', async () => {
    const loadUser = vi.fn().mockRejectedValue(Object.assign(new Error('만료'), { status: 401 }));
    const { result, setToken } = setup({ initialToken: 'expired-token', loadUser });
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(setToken).toHaveBeenCalledWith(null);
    expect(result.current.token).toBeNull();
    expect(result.current.user).toBeNull();
  });

  it('login(newToken) — 토큰 세팅 후 loadUser가 실행되어 user가 채워진다', async () => {
    const loadUser = vi.fn().mockResolvedValue({ id: 2, name: '독자' });
    const { result } = setup({ loadUser });
    expect(result.current.loading).toBe(false);

    act(() => result.current.login('new-token'));

    await waitFor(() => expect(result.current.user).toEqual({ id: 2, name: '독자' }));
    expect(result.current.token).toBe('new-token');
    expect(loadUser).toHaveBeenCalledTimes(1);
  });

  it('logout() — token/user를 즉시 초기화한다', async () => {
    const loadUser = vi.fn().mockResolvedValue({ id: 3 });
    const { result } = setup({ initialToken: 't1', loadUser });
    await waitFor(() => expect(result.current.user).toEqual({ id: 3 }));

    act(() => result.current.logout());

    expect(result.current.token).toBeNull();
    expect(result.current.user).toBeNull();
  });

  it("userKey 옵션 — potato처럼 'operator'로 지정하면 그 필드명으로 노출된다", async () => {
    const loadUser = vi.fn().mockResolvedValue({ id: 9, role: 'ops' });
    const { result } = setup({ initialToken: 't1', loadUser, userKey: 'operator' });
    await waitFor(() => expect(result.current.operator).toEqual({ id: 9, role: 'ops' }));
    expect(result.current.user).toBeUndefined();
  });
});
