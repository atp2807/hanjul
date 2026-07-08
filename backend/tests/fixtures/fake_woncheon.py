"""Fake woncheon 포트/레포 — WoncheonReportingService 단위 테스트용.

Protocol 구현 대상:
  src.features.woncheon.domain.models.WoncheonReportingPort (FakeWoncheonAdapter)
  src.features.woncheon.domain.models.WithholdingRepository (FakeWithholdingRepository)
"""
from datetime import datetime
from uuid import UUID

from src.features.woncheon.domain.models import (
    ReportResult,
    UnreportedPayoutView,
    WithholdingSubjectView,
)


class FakeWoncheonAdapter:
    """호출 기록 + 멱등성 시뮬레이션 — 같은 payout_id 재호출은 첫 결과를 그대로 반환
    (woncheon 의 Idempotency-Key=payout_id 멱등 계약을 흉내)."""

    def __init__(self, ok: bool = True, fail_message: str = "fake failure"):
        self.ok = ok
        self.fail_message = fail_message
        self.calls: list[dict] = []
        self._results: dict[UUID, ReportResult] = {}

    async def report_payment(
        self, payout_id: UUID, gross_amount: int, income_type_code: str, payee_resident_number: str
    ) -> ReportResult:
        self.calls.append(
            {
                "payout_id": payout_id,
                "gross_amount": gross_amount,
                "income_type_code": income_type_code,
                "payee_resident_number": payee_resident_number,
            }
        )
        if payout_id in self._results:
            return self._results[payout_id]  # 멱등 — 재호출은 첫 결과 재사용
        result = (
            ReportResult(ok=True, external_reference=f"wc-{payout_id}")
            if self.ok
            else ReportResult(ok=False, message=self.fail_message)
        )
        self._results[payout_id] = result
        return result


class FakeWithholdingRepository:
    def __init__(self) -> None:
        self.subjects: dict[UUID, WithholdingSubjectView] = {}
        self.payout_gross: dict[UUID, int] = {}
        self.reported_at: dict[UUID, datetime] = {}

    # ── 테스트 준비 헬퍼 ──────────────────────────────
    def seed_payout(self, payout_id: UUID, gross_amt: int) -> None:
        self.payout_gross[payout_id] = gross_amt

    # ── WithholdingRepository ─────────────────────────
    async def get_subject(self, payout_id: UUID) -> WithholdingSubjectView | None:
        return self.subjects.get(payout_id)

    async def upsert_subject(
        self, payout_id: UUID, resident_no_enc: str, income_type_code: str
    ) -> WithholdingSubjectView:
        view = WithholdingSubjectView(
            payout_id=payout_id, resident_no_enc=resident_no_enc,
            income_type_code=income_type_code, created_at=datetime.now(),
        )
        self.subjects[payout_id] = view
        return view

    async def get_payout_gross(self, payout_id: UUID) -> int | None:
        return self.payout_gross.get(payout_id)

    async def mark_reported(self, payout_id: UUID, when: datetime) -> None:
        self.reported_at[payout_id] = when

    async def list_unreported_paid(self) -> list[UnreportedPayoutView]:
        return [
            UnreportedPayoutView(
                payout_id=pid, author_id=pid, gross_amt=gross, net_amt=gross,
                paid_at=datetime.now(), has_subject=pid in self.subjects,
            )
            for pid, gross in self.payout_gross.items()
            if pid not in self.reported_at
        ]
