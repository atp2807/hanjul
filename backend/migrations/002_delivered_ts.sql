-- 002_delivered_ts.sql — 전자책 제공 개시(첫 전체열람/다운로드) 시각 추적
--
-- 환불세이프(청약철회 제한 발동, 전자상거래법 §17①/②) 판정용. 출금가능액(payable)에는
-- 환불세이프 주문(= 이 컬럼이 채워졌거나 결제 후 7일 경과)의 정산분만 포함한다
-- (payouts/infrastructure/payout_repo.py:_unpaid_stmt). NULL = 아직 열람/다운로드 안 됨.
--
-- 001과 달리 멱등 처리 불필요 — migrate.py의 migration_history가 재적용을 막아준다.

ALTER TABLE bill.book_order ADD COLUMN delivered_ts timestamptz;
