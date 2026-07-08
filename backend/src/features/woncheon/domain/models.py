"""woncheon 원천징수 신고 커넥터 도메인 — 포트 + 뷰 + 예외 (lr-ac61f505 스켈레톤).

한줄 ebook은 지급명세서/월별집계/홈택스 신고엔진을 재구축하지 않는다 — 자매 프로젝트
hanjul_woncheon(B2B 세무 자동화 API)으로 payout PAID 이벤트를 전달하는 커넥터만.

⚠️ 이 스켈레톤은 실 네트워크 호출을 하지 않는다 — (a) 한줄이 아직 woncheon 테넌트로
등록되지 않았고(api_key 없음) (b) 인세 소득구분(사업소득 3.3% vs 기타소득 8%)이 세무사
미판정이며 (c) woncheon 배포 도메인이 미확정이기 때문(lr-ac61f505). 라이브 어댑터는
설정값이 없으면 즉시 명시적으로 실패한다(조용한 무동작 금지) — 테스트는 FakeWoncheonAdapter로.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID


@dataclass
class ReportResult:
    """신고 시도 결과 — ok=False 는 예외가 아니라 "보류"(주민번호 미등록 등)와 "실패"(설정
    미비·네트워크 오류) 둘 다 포괄. message 에 사유."""
    ok: bool
    external_reference: str | None = None
    message: str | None = None


@dataclass
class WithholdingSubjectView:
    payout_id: UUID
    resident_no_enc: str
    income_type_code: str
    created_at: datetime


@dataclass
class UnreportedPayoutView:
    """운영자 조회용 — PAID인데 아직 woncheon 신고가 안 된 payout."""
    payout_id: UUID
    author_id: UUID
    gross_amt: int
    net_amt: int
    paid_at: datetime
    has_subject: bool  # False면 주민번호 미등록 — 신고 자체가 보류중(먼저 등록 필요)


class WoncheonNotConfigured(RuntimeError):
    """WONCHEON_API_BASE/WONCHEON_API_KEY 미설정 — woncheon 테넌트 등록 전(lr-ac61f505).

    조용히 넘어가지 않도록 어댑터가 명시적으로 raise. 호출부(WoncheonReportingService)가
    best-effort로 잡아 ReportResult(ok=False)로 변환하므로, 이 예외가 payout 지급 자체를
    막지는 않는다.
    """


class WoncheonReportingPort(Protocol):
    """hanjul_woncheon 연동 계약(조사 완료, lr-ac61f505):
    POST {base}/api/v1/payments, X-API-Key 헤더, Idempotency-Key=payout_id 로 멱등.
    """
    async def report_payment(
        self, payout_id: UUID, gross_amount: int, income_type_code: str, payee_resident_number: str
    ) -> ReportResult: ...


class WithholdingRepository(Protocol):
    async def get_subject(self, payout_id: UUID) -> WithholdingSubjectView | None: ...

    async def upsert_subject(
        self, payout_id: UUID, resident_no_enc: str, income_type_code: str
    ) -> WithholdingSubjectView: ...

    async def get_payout_gross(self, payout_id: UUID) -> int | None: ...

    async def mark_reported(self, payout_id: UUID, when: datetime) -> None: ...

    async def list_unreported_paid(self) -> list[UnreportedPayoutView]: ...
