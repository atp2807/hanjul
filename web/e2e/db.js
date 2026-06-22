// E2E DB 접속 정보 — 로컬 기본값 + CI 환경변수 오버라이드.
// CI(GitHub Actions)는 postgres 서비스 컨테이너(user/password 인증)를 주입한다.
export const PGHOST = process.env.PGHOST || '127.0.0.1';
export const PGPORT = process.env.PGPORT || '5432';
export const PGUSER = process.env.PGUSER || 'daviy';
export const PGPASSWORD = process.env.PGPASSWORD || '';
export const E2E_DB_NAME = process.env.E2E_DB || 'hanjul_e2e';

// 백엔드 파이썬 (py3.12 + asyncpg). 로컬은 .venv312, CI는 BACKEND_PY로 지정.
export const BACKEND_PY = process.env.BACKEND_PY || '.venv312/bin/python';

export function databaseUrl(db = E2E_DB_NAME) {
  const auth = PGPASSWORD ? `${PGUSER}:${encodeURIComponent(PGPASSWORD)}` : PGUSER;
  return `postgresql+asyncpg://${auth}@${PGHOST}:${PGPORT}/${db}`;
}
