// E2E 전역 셋업 — 매 실행마다 깨끗한 hanjul_e2e DB를 만들고 마이그레이션.
// 결정적 시작(빈 DB)이라야 목록/구매/매출 단언이 흔들리지 않는다.
import { execSync } from 'node:child_process';
import { existsSync } from 'node:fs';

const DB = process.env.E2E_DB || 'hanjul_e2e';
const PGHOST = process.env.PGHOST || '127.0.0.1';
const PGUSER = process.env.PGUSER || 'daviy';

// psql/createdb 클라이언트 위치 (homebrew). PATH에 있으면 그대로 사용.
const PG_BIN = ['/opt/homebrew/opt/postgresql@16/bin', '/opt/homebrew/opt/postgresql@15/bin']
  .find((p) => existsSync(`${p}/createdb`)) || '';
const bin = (cmd) => (PG_BIN ? `${PG_BIN}/${cmd}` : cmd);

export default function globalSetup() {
  const env = { ...process.env, PGHOST, PGUSER };
  execSync(`${bin('dropdb')} --if-exists ${DB}`, { env, stdio: 'inherit' });
  execSync(`${bin('createdb')} ${DB}`, { env, stdio: 'inherit' });
  // 스키마 — py3.12 venv(asyncpg). DATABASE_URL env가 .env보다 우선(pydantic).
  execSync('.venv312/bin/alembic upgrade head', {
    cwd: '../backend',
    env: { ...process.env, DATABASE_URL: `postgresql+asyncpg://${PGUSER}@${PGHOST}:5432/${DB}` },
    stdio: 'inherit',
  });
}
