-- 운영자(potato) DB 권한분리 — 고객 커넥션이 potato 스키마를 물리적으로 못 읽게.
--
-- ⚠️ 프로덕션 DB 롤 변경. 잘못 적용하면 서비스 다운. 반드시 순서·백업 확인 후 psql로 수동 실행.
-- 전제: 기존 앱 접속 유저 = 'hanjul'(고객·운영자 공용이던 유저). RDS라면 마스터로 접속해 실행.
--
-- 효과: hanjul(고객 유저)은 potato 스키마 접근 불가. potato 전용 유저만 potato.operator/
--       audit_log 접근. 앱은 POTATO_DATABASE_URL로 potato_user 커넥션을 별도로 씀
--       (get_potato_auth_service / get_audit_service 만 이 세션 사용).

-- 1) 운영자 전용 DB 유저 (저권한 — potato 스키마만)
CREATE ROLE potato_user WITH LOGIN PASSWORD '__CHANGE_ME__';

GRANT USAGE ON SCHEMA potato TO potato_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA potato TO potato_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA potato
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO potato_user;
-- audit_log.operator_id → potato.operator FK 검증은 테이블 소유자 트리거로 돌아가므로
-- potato_user 에 다른 스키마 권한이 없어도 무방(감사 결과 확인됨).

-- 2) 고객 유저(hanjul)에서 potato 스키마 회수 — 핵심 방어선
REVOKE ALL ON ALL TABLES IN SCHEMA potato FROM hanjul;
REVOKE ALL ON SCHEMA potato FROM hanjul;
ALTER DEFAULT PRIVILEGES IN SCHEMA potato REVOKE ALL ON TABLES FROM hanjul;
-- 주의: 마이그레이션(migrate.py, raw SQL)은 hanjul 로 도는데, potato 테이블 생성/변경이
--       필요하면 마이그레이션은 potato 스키마 소유권을 가진 유저로 돌리거나, DDL 시에만 일시 GRANT.
--       (현 구조: 마이그레이션 러너가 스키마 소유자여야 함 → 아래 3) 참고)

-- 3) 마이그레이션 유저 처리 (택1)
--   a. hanjul 이 스키마 소유자면: potato 테이블 DDL 은 hanjul 로 계속 가능하되 DML 은 위에서 REVOKE.
--      → REVIEW: REVOKE 가 소유자에겐 안 먹을 수 있음(소유자는 항상 접근). 이 경우 (b) 권장.
--   b. potato 스키마/테이블 소유권을 potato_user 로 이전:
--      ALTER SCHEMA potato OWNER TO potato_user;
--      ALTER TABLE potato.operator OWNER TO potato_user;
--      ALTER TABLE potato.audit_log OWNER TO potato_user;
--      → 그러면 마이그레이션 러너(hanjul)가 potato 테이블 DDL 불가 → potato 마이그레이션만 potato_user 로 실행.
--      초기 규모에선 (b)가 깔끔(potato 스키마를 potato_user 소유로 완전 격리).

-- 적용 후: 앱 .env 에 POTATO_DATABASE_URL 주입
--   POTATO_DATABASE_URL=postgresql+asyncpg://potato_user:__PW__@<host>:5432/<db>
-- 미주입 시 앱은 메인 DATABASE_URL 재사용(격리 없음, dev 동작).

-- 검증 (potato_user 로 접속해 고객 스키마 못 읽는지 / hanjul 로 potato 못 읽는지):
--   SET ROLE hanjul;  SELECT * FROM potato.operator;   -- permission denied 여야 정상
