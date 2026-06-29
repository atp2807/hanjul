import { createContext, useCallback, useContext, useEffect, useState } from 'react';

import { api, getToken, setToken } from './api';

const OpsAuthContext = createContext(null);

export function OpsAuthProvider({ children }) {
  const [token, setTokenState] = useState(() => getToken());
  const [operator, setOperator] = useState(null);
  const [loading, setLoading] = useState(!!getToken());

  useEffect(() => {
    if (!token) {
      setOperator(null);
      setLoading(false);
      return;
    }
    setLoading(true);
    api
      .me()
      .then(setOperator)
      .catch(() => {
        setToken(null);
        setTokenState(null);
        setOperator(null);
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
    setOperator(null);
  }, []);

  return (
    <OpsAuthContext.Provider value={{ token, operator, loading, login, logout }}>
      {children}
    </OpsAuthContext.Provider>
  );
}

export function useOps() {
  return useContext(OpsAuthContext);
}
