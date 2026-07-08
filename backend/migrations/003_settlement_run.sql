-- 003_settlement_run.sql — 매주 수요일 고정 정산 배치(lr-a0a8bda9) 멱등 가드
--
-- run_date UNIQUE 제약으로 "이 수요일 배치를 이미 실행했는가"를 보장한다. 스케줄러가
-- 30초마다 깨어나 같은 요일에 여러 번 호출해도(main.py _publish_scheduler) 최초 1회만
-- 실제 payout을 만들고 이후 호출은 claim 실패로 즉시 0 반환(PayoutService.run_weekly_settlement).
-- 002와 마찬가지로 멱등 처리 불필요 — migrate.py의 migration_history가 재적용을 막아준다.

CREATE TABLE bill.settlement_run (
    id uuid PRIMARY KEY,
    run_dt date NOT NULL UNIQUE,
    payout_cnt integer NOT NULL DEFAULT 0,
    created_ts timestamptz NOT NULL DEFAULT now()
);
