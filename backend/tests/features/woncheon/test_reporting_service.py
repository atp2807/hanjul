"""WoncheonReportingService 단위 — 최소수집(주민번호) + PAID 후 best-effort 신고 (Fake)."""
import uuid

import pytest
from src.features.payouts.application.crypto import decrypt
from src.features.woncheon.application.reporting_service import WoncheonReportingService
from src.shared.errors import ValidationError

from tests.fixtures.fake_woncheon import FakeWithholdingRepository, FakeWoncheonAdapter

RESIDENT_NO = "9001011234567"  # 13자리, 가상 예시


# ── 대상자 등록(최소수집) ─────────────────────────────
async def test_register_subject_encrypts_resident_number():
    repo = FakeWithholdingRepository()
    svc = WoncheonReportingService(repo, FakeWoncheonAdapter(), default_income_type_code="940906")
    payout_id = uuid.uuid4()

    await svc.register_subject(payout_id, RESIDENT_NO)

    stored = repo.subjects[payout_id]
    assert stored.resident_no_enc != RESIDENT_NO  # 평문 그대로 저장 안 됨
    assert decrypt(stored.resident_no_enc) == RESIDENT_NO  # 복호화하면 원문
    assert stored.income_type_code == "940906"  # 설정 기본값 사용


async def test_register_subject_uses_explicit_income_type_over_default():
    repo = FakeWithholdingRepository()
    svc = WoncheonReportingService(repo, FakeWoncheonAdapter(), default_income_type_code="940906")
    payout_id = uuid.uuid4()

    await svc.register_subject(payout_id, RESIDENT_NO, income_type_code="75")

    assert repo.subjects[payout_id].income_type_code == "75"


async def test_register_subject_raises_when_no_income_type_code_anywhere():
    """세무사 판정 전 하드코딩 금지 — 기본값도 명시값도 없으면 명확히 거부."""
    repo = FakeWithholdingRepository()
    svc = WoncheonReportingService(repo, FakeWoncheonAdapter(), default_income_type_code=None)

    with pytest.raises(ValidationError):
        await svc.register_subject(uuid.uuid4(), RESIDENT_NO)


async def test_register_subject_rejects_malformed_resident_number():
    repo = FakeWithholdingRepository()
    svc = WoncheonReportingService(repo, FakeWoncheonAdapter(), default_income_type_code="940906")

    with pytest.raises(ValidationError):
        await svc.register_subject(uuid.uuid4(), "12345")  # 13자리 아님
    with pytest.raises(ValidationError):
        await svc.register_subject(uuid.uuid4(), "abcdefghijklm")  # 숫자 아님


# ── PAID 후 신고 (best-effort) ────────────────────────
async def test_report_paid_holds_when_no_subject_registered():
    repo = FakeWithholdingRepository()
    adapter = FakeWoncheonAdapter()
    svc = WoncheonReportingService(repo, adapter, default_income_type_code="940906")
    payout_id = uuid.uuid4()
    repo.seed_payout(payout_id, gross_amt=10000)

    result = await svc.report_paid(payout_id)

    assert result.ok is False
    assert "주민번호" in result.message
    assert adapter.calls == []  # 포트 호출 자체가 안 됨


async def test_report_paid_holds_when_payout_missing():
    repo = FakeWithholdingRepository()
    svc = WoncheonReportingService(repo, FakeWoncheonAdapter(), default_income_type_code="940906")
    payout_id = uuid.uuid4()
    # 주민번호는 등록됐지만 payout gross 시딩이 없는 경우
    await svc.register_subject(payout_id, RESIDENT_NO)

    result = await svc.report_paid(payout_id)

    assert result.ok is False
    assert "payout" in result.message.lower() or "찾을 수 없음" in result.message


async def test_report_paid_success_calls_port_with_correct_args_and_marks_reported():
    repo = FakeWithholdingRepository()
    adapter = FakeWoncheonAdapter(ok=True)
    svc = WoncheonReportingService(repo, adapter, default_income_type_code="940906")
    payout_id = uuid.uuid4()
    repo.seed_payout(payout_id, gross_amt=6769)
    await svc.register_subject(payout_id, RESIDENT_NO)

    result = await svc.report_paid(payout_id)

    assert result.ok is True
    assert len(adapter.calls) == 1
    call = adapter.calls[0]
    assert call["payout_id"] == payout_id  # external_payment_id 로 쓰일 값
    assert call["gross_amount"] == 6769
    assert call["income_type_code"] == "940906"
    assert call["payee_resident_number"] == RESIDENT_NO  # 어댑터에는 복호화된 원문 전달
    assert payout_id in repo.reported_at  # 성공 시에만 마킹


async def test_report_paid_failure_does_not_mark_reported():
    repo = FakeWithholdingRepository()
    adapter = FakeWoncheonAdapter(ok=False, fail_message="테넌트 미등록")
    svc = WoncheonReportingService(repo, adapter, default_income_type_code="940906")
    payout_id = uuid.uuid4()
    repo.seed_payout(payout_id, gross_amt=1000)
    await svc.register_subject(payout_id, RESIDENT_NO)

    result = await svc.report_paid(payout_id)

    assert result.ok is False
    assert payout_id not in repo.reported_at  # 실패 — 재시도 가능하게 미마킹


async def test_report_paid_swallows_port_exception_as_hold():
    """어댑터가 예외(WoncheonNotConfigured 등)를 던져도 서비스는 흡수해 ok=False 로 반환."""
    class RaisingAdapter:
        async def report_payment(self, **kwargs):
            raise RuntimeError("WONCHEON_API_KEY 미설정")

    repo = FakeWithholdingRepository()
    svc = WoncheonReportingService(repo, RaisingAdapter(), default_income_type_code="940906")
    payout_id = uuid.uuid4()
    repo.seed_payout(payout_id, gross_amt=1000)
    await svc.register_subject(payout_id, RESIDENT_NO)

    result = await svc.report_paid(payout_id)  # 예외가 여기까지 전파되면 실패

    assert result.ok is False
    assert "WONCHEON_API_KEY" in result.message
    assert payout_id not in repo.reported_at


async def test_report_paid_idempotent_repeat_call_reuses_first_result():
    """같은 payout_id 재호출 — woncheon 의 Idempotency-Key 계약을 Fake 로 흉내."""
    repo = FakeWithholdingRepository()
    adapter = FakeWoncheonAdapter(ok=True)
    svc = WoncheonReportingService(repo, adapter, default_income_type_code="940906")
    payout_id = uuid.uuid4()
    repo.seed_payout(payout_id, gross_amt=5000)
    await svc.register_subject(payout_id, RESIDENT_NO)

    r1 = await svc.report_paid(payout_id)
    r2 = await svc.report_paid(payout_id)  # 수동 재시도 스크립트가 다시 부르는 상황 흉내

    assert r1.ok is True and r2.ok is True
    assert r1.external_reference == r2.external_reference
    assert len(adapter.calls) == 2  # 호출 자체는 두 번 갔지만 결과는 동일(멱등)


async def test_list_unreported_reports_has_subject_flag():
    repo = FakeWithholdingRepository()
    svc = WoncheonReportingService(repo, FakeWoncheonAdapter(), default_income_type_code="940906")
    with_subject = uuid.uuid4()
    without_subject = uuid.uuid4()
    repo.seed_payout(with_subject, gross_amt=1000)
    repo.seed_payout(without_subject, gross_amt=2000)
    await svc.register_subject(with_subject, RESIDENT_NO)

    rows = await svc.list_unreported()

    by_id = {r.payout_id: r for r in rows}
    assert by_id[with_subject].has_subject is True
    assert by_id[without_subject].has_subject is False
