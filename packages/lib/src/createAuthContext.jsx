import { createContext, useCallback, useContext, useEffect, useState } from 'react';

// 공용 인증 컨텍스트 팩토리 — web(user)·potato(operator)가 loadUser·필드명만 주입.
// 토큰 있으면 loadUser로 유저 로드, 실패(만료/위조)하면 로그아웃.

/**
 * @param {object} opts
 * @param {() => string|null} opts.getToken
 * @param {(t: string|null) => void} opts.setToken
 * @param {() => Promise<object>} opts.loadUser  토큰 유효 시 유저 정보 로드 (getMe / api.me)
 * @param {string} [opts.userKey='user']         컨텍스트 값의 유저 필드명 (web='user', potato='operator')
 * @returns {{ AuthProvider, useAuthContext }}
 */
export function createAuthContext({ getToken, setToken, loadUser, userKey = 'user' }) {
  const Ctx = createContext(null);

  function AuthProvider({ children }) {
    const [token, setTokenState] = useState(() => getToken());
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(!!getToken());

    useEffect(() => {
      if (!token) {
        setUser(null);
        setLoading(false);
        return;
      }
      setLoading(true);
      loadUser()
        .then(setUser)
        .catch(() => {
          setToken(null);
          setTokenState(null);
          setUser(null);
        })
        .finally(() => setLoading(false));
    }, [token]);

    const login = useCallback((newToken) => {
      setToken(newToken);
      setTokenState(newToken);
    }, []);

    const logout = useCallback(() => {
      setToken(null);
      setTokenState(null);
      setUser(null);
    }, []);

    const value = { token, [userKey]: user, loading, login, logout };
    return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
  }

  const useAuthContext = () => useContext(Ctx);
  return { AuthProvider, useAuthContext };
}
