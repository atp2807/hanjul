// E2E 전역 셋업 — 매 실행마다 깨끗한 e2e DB를 만들고 마이그레이션.
// 결정적 시작(빈 DB)이라야 목록/구매/매출 단언이 흔들리지 않는다.
import { execSync } from 'node:child_process';
import { existsSync } from 'node:fs';

import { BACKEND_PY, databaseUrl, E2E_DB_NAME, PGHOST, PGPASSWORD, PGPORT, PGUSER } from './db.js';

// psql/createdb 클라이언트 위치. PATH(CI·리눅스)에 있으면 그대로, 없으면 homebrew(맥) 탐색.
const PG_BIN = ['/opt/homebrew/opt/postgresql@16/bin', '/opt/homebrew/opt/postgresql@15/bin']
  .find((p) => existsSync(`${p}/createdb`)) || '';
const bin = (cmd) => (PG_BIN ? `${PG_BIN}/${cmd}` : cmd);

export default function globalSetup() {
  // createdb/dropdb는 PG* 환경변수로 접속(비밀번호 포함)
  const env = { ...process.env, PGHOST, PGPORT, PGUSER, PGPASSWORD };
  execSync(`${bin('dropdb')} --if-exists ${E2E_DB_NAME}`, { env, stdio: 'inherit' });
  execSync(`${bin('createdb')} ${E2E_DB_NAME}`, { env, stdio: 'inherit' });
  // 스키마 — py3.12(asyncpg). DATABASE_URL env가 .env보다 우선(pydantic).
  execSync(`${BACKEND_PY} migrate.py`, {
    cwd: '../backend',
    env: { ...process.env, DATABASE_URL: databaseUrl() },
    stdio: 'inherit',
  });
}
