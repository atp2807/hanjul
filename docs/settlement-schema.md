# 정산·출금 스키마 설계 (돈 모델)

> 구조: **플랫폼=판매자, 작가=라이선서, 인세=로열티 지급**(→ payment-tax.md, 전자금융업 회피 유지). 원천징수 **사업소득 3.3% 디폴트**. 전자책 면세=ISBN/ECN.
> 현재: `bill.book_order`(구매) + `bill.settlement`(주문당 작가몫 계산, 원천징수 3.3% 계산 이미 있음)만 존재. **작가에게 지급할 인프라가 없음** → 아래 신설.

## 개념 흐름
```
판매 confirm ──▶ settlement(주문당 작가몫 스냅샷, PENDING)
                      │
   [월 마감 배치] ────▶ payout(작가×월 집계: gross 합계 → 원천징수 3.3% → net)  status: DRAFT
                      │         └ settlement.payout_id 로 묶음
   작가 출금가능 ─────▶ REQUESTED ──[운영자 승인]──▶ APPROVED ──[실이체]──▶ PAID
                                                                    └ FAILED(반려/실패)
   환불 발생 ────────▶ 역정산: ledger REFUND(-) + 해당 settlement REVERSED
                        (미지급이면 payout에서 차감 / 지급완료면 다음 payout 음수 이월)
   모든 돈 이동 ──────▶ ledger_entry(append-only, 대사·감사·지급명세서 근거)
```

## 신설 테이블 (`bill` 스키마)

### `bill.bank_account` — 작가 출금계좌
| 컬럼 | 타입 | 비고 |
|---|---|---|
| id | UUID PK | |
| account_id | UUID FK usr.account | 작가 |
| holder_name | str | 예금주(실명확인) |
| bank_cd | str(10) | 은행코드 |
| account_no_enc | str | **암호화/토큰화 저장**(개인정보 안전성 §29) |
| verified_yn | bool | 1원인증 등 계좌검증 |
| primary_yn | bool | 기본 출금계좌 |
| created_ts/updated_ts | ts | |
> 계좌번호는 민감 → 앱단 암호화. 개인정보처리방침에 항목·위탁(정산이체) 기재.

### `bill.payout` — 월 배치 지급 (작가×기간)
| 컬럼 | 타입 | 비고 |
|---|---|---|
| id | UUID PK | |
| author_id | UUID FK usr.account | |
| period_ym | str(6) | 정산 대상월 `YYYYMM` |
| status_cd | str(20) | DRAFT→REQUESTED→APPROVED→PAID / FAILED / HOLD |
| gross_amt | Numeric(15,0) | 작가몫 합계(원천징수 전) |
| withholding_amt | Numeric(15,0) | **지급시점 3.3% (집계액 기준)** |
| adjust_amt | Numeric(15,0) | 역정산·이월(음수 가능) |
| net_amt | Numeric(15,0) | 실지급 = gross - withholding + adjust |
| bank_account_id | UUID FK bill.bank_account | 지급 시점 스냅샷 |
| income_type_cd | str(20) | BIZ(사업3.3%)/ETC(기타8.8%) — 디폴트 BIZ |
| requested_ts/approved_ts/paid_ts | ts | 상태 타임스탬프 |
| approved_by | UUID FK potato.operator | 승인 운영자(감사) |
| pg_transfer_id | str | 이체 참조(지급대행/이체 API) |
| memo | text | |
| UNIQUE(author_id, period_ym) | | 월 1건 |

### `bill.settlement` (기존) — 확장
- 추가: `payout_id` UUID FK bill.payout **nullable**(묶이면 채움), `status_cd`(PENDING→SETTLED→REVERSED).
- ★**원천징수 타이밍 결정**: 기존 per-order `withholding_amt`는 **표시용 추정치**로 두고, **법적 원천징수·지급명세서는 payout(월 집계)에서 확정**. 이유: 원천징수는 지급시점·지급액 기준이라 주문별 반올림 합≠집계 반올림. payout.gross_amt=Σsettlement.gross, withholding=round(gross×3.3%).

### `bill.ledger_entry` — 불변 원장(append-only)
| 컬럼 | 타입 | 비고 |
|---|---|---|
| id | UUID PK | |
| entry_ts | ts | |
| account_id | UUID | 귀속 주체(작가/플랫폼) |
| type_cd | str(20) | SALE·PLATFORM_FEE·REFUND·WITHHOLDING·PAYOUT |
| amount_amt | Numeric(15,0) | **부호 있음**(+수입/−지출) |
| ref_type/ref_id | str/UUID | order/settlement/payout 참조 |
| memo | text | |
> 절대 UPDATE/DELETE 안 함. 대사(reconcile)·감사·지급명세서·분쟁의 단일 진실.

## `pub.book` 세금 필드 (부가세 분기)
- 기존 `isbn` 활용 + 추가: `ecn`(KEPA 전자출판물 인증번호), `tax_exempt_yn`(면세 = ISBN/ECN 있고 요건 충족).
- 주문 금액 도출 시 면세/과세 분기 → 증빙(면세 계산서 vs 세금계산서 vs 현금영수증) 결정.

## `bill.book_order` 증빙 필드 (선택)
- `receipt_type_cd`(CARD 전표 / CASH 현금영수증 / NONE), `cash_receipt_no`. 현금/이체 결제 시 현금영수증 자동발급(요청 시 1원부터, 10만↑ 의무).

## 상태기계 (payout)
`DRAFT`(월마감 자동집계) → `REQUESTED`(작가 출금신청 or 자동확정) → `APPROVED`(운영자·potato Phase2) → `PAID`(이체완료) / `FAILED`(계좌오류 등→재시도) / `HOLD`(분쟁·역정산 대기).

## 세무 훅
- **간이지급명세서(사업소득)**: payout PAID건을 월별 집계 → 다음달 말 제출용 데이터. 원천징수영수증 작가 교부.
- **면세/과세**: book.tax_exempt_yn 기준. 혼재 시 매입세액 안분(과세:면세 공급가액 비율).
- **현금영수증**: 현금·이체 결제만, 자동발급.

## ⚠️ 확정 전 확인 (payment-tax.md와 연동)
1. (세무) 원천징수 per-order vs 월집계 — 지급명세서 정합 위해 **월집계 권장**, 세무사 확인.
2. (세무) 작가 소득구분(BIZ/ETC), 저작자 외 지급.
3. (법무) 실이체 수단 — 대량이체 API/펌뱅킹이 "지급대행/자금이체업"에 걸리지 않는 선(자기채무 이행 이체는 무방하나 규모·형태 확인).
4. (세무) 면세 귀속주체·현금영수증 발급주체(PG 경유).

## 구현 순서(제안)
1. `bank_account` + 계좌등록/검증 → 2. `payout` + 월마감 배치(settlement 집계) → 3. 작가 출금신청 + potato 승인(Phase2) → 4. 실이체 연동 → 5. `ledger_entry` 병행 기록 → 6. 지급명세서·현금영수증 자동화.
