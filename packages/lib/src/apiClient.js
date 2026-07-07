// 공용 API 클라이언트 팩토리 — web·potato가 토큰키만 달리해 생성.
// 베이스: dev는 '' (vite proxy), prod는 VITE_API_BASE_URL. 토큰 있으면 Bearer 자동.

/**
 * @param {string} tokenKey localStorage 토큰 키 (web='hanjul_token', potato='potato_token')
 * @returns {{ getToken, setToken, get, post, put, del, upload, download, request }}
 */
export function createApiClient(tokenKey) {
  const BASE = import.meta.env.VITE_API_BASE_URL || '';

  const getToken = () => localStorage.getItem(tokenKey);
  const setToken = (token) => {
    if (token) localStorage.setItem(tokenKey, token);
    else localStorage.removeItem(tokenKey);
  };

  // 에러 body 의 detail(서버가 주는 사용자용 한국어 문구)을 살려서 던진다.
  // detail 이 문자열일 때만 사용 (FastAPI 422 는 배열이라 제외) — err.detail 로 노출.
  async function toError(res, path) {
    let detail = null;
    try {
      const body = await res.json();
      if (typeof body?.detail === 'string') detail = body.detail;
    } catch { /* body 없음/JSON 아님 */ }
    const err = new Error(detail || `API ${res.status}: ${path}`);
    err.status = res.status;
    err.detail = detail;
    return err;
  }

  async function request(path, options = {}) {
    const token = getToken();
    const res = await fetch(`${BASE}/api${path}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(options.headers || {}),
      },
    });
    if (!res.ok) throw await toError(res, path);
    if (res.status === 204) return null; // No Content
    return res.json();
  }

  // 인증 첨부 파일 다운로드 (EPUB·ONIX 등) — 브라우저 저장 다이얼로그 트리거.
  async function download(path, fallbackName) {
    const token = getToken();
    const res = await fetch(`${BASE}/api${path}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!res.ok) throw await toError(res, path);
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
    if (!res.ok) throw await toError(res, path);
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
    // get/post/put/del은 아직 options.headers를 안 받지만(도달 불가), request()는 커스텀 헤더
    // 확장을 이미 지원한다. 향후 그 확장 지점을 쓰는 API·회귀테스트를 위해 직접 노출.
    request,
  };
}
