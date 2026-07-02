// 공용 API 클라이언트 팩토리 — web·potato가 토큰키만 달리해 생성.
// 베이스: dev는 '' (vite proxy), prod는 VITE_API_BASE_URL. 토큰 있으면 Bearer 자동.

/**
 * @param {string} tokenKey localStorage 토큰 키 (web='hanjul_token', potato='potato_token')
 * @returns {{ getToken, setToken, get, post, put, del, upload, download }}
 */
export function createApiClient(tokenKey) {
  const BASE = import.meta.env.VITE_API_BASE_URL || '';

  const getToken = () => localStorage.getItem(tokenKey);
  const setToken = (token) => {
    if (token) localStorage.setItem(tokenKey, token);
    else localStorage.removeItem(tokenKey);
  };

  async function request(path, options = {}) {
    const token = getToken();
    const res = await fetch(`${BASE}/api${path}`, {
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(options.headers || {}),
      },
      ...options,
    });
    if (!res.ok) {
      const err = new Error(`API ${res.status}: ${path}`);
      err.status = res.status;
      throw err;
    }
    if (res.status === 204) return null; // No Content
    return res.json();
  }

  // 인증 첨부 파일 다운로드 (EPUB·ONIX 등) — 브라우저 저장 다이얼로그 트리거.
  async function download(path, fallbackName) {
    const token = getToken();
    const res = await fetch(`${BASE}/api${path}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!res.ok) {
      const err = new Error(`API ${res.status}: ${path}`);
      err.status = res.status;
      throw err;
    }
    const blob = await res.blob();
    const cd = res.headers.get('Content-Disposition') || '';
    const m = cd.match(/filename="?([^"]+)"?/);
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = (m && m[1]) || fallbackName;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  }

  // 파일 업로드 (multipart). Content-Type은 브라우저가 boundary와 자동 설정 → 지정 금지.
  async function upload(path, formData) {
    const token = getToken();
    const res = await fetch(`${BASE}/api${path}`, {
      method: 'POST',
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: formData,
    });
    if (!res.ok) {
      const err = new Error(`API ${res.status}: ${path}`);
      err.status = res.status;
      throw err;
    }
    return res.json();
  }

  return {
    getToken,
    setToken,
    get: (path) => request(path),
    post: (path, body) => request(path, { method: 'POST', body: body ? JSON.stringify(body) : undefined }),
    put: (path, body) => request(path, { method: 'PUT', body: body ? JSON.stringify(body) : undefined }),
    del: (path) => request(path, { method: 'DELETE' }),
    upload,
    download,
  };
}
