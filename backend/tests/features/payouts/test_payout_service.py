"""PayoutService 단위 — 계좌 검증/암호화 + 출금 신청/상태전이 (Fake repo)."""
import uuid
from datetime import UTC, datetime

import pytest
from src.features.payouts.application.crypto import decrypt
from src.features.payouts.application.payout_service import PayoutService
from src.features.payouts.domain.models import (
    APPROVED,
    PAID,
    REJECTED,
    REQUESTED,
    InvalidPayoutState,
    NoBankAccount,
    NothingToPayout,
    PayableSummary,
    PayoutNotFound,
    PayoutView,
)
from src.shared.errors import ValidationError

from tests.fixtures.fake_payout_repo import FakePayoutRepository

NOW = datetime(2026, 7, 1, tzinfo=UTC)


def _payout(author_id, status=REQUESTED) -> PayoutView:
    return PayoutView(
        id=uuid.uuid4(), author_id=author_id, status=status,
        gross_amt=10000, withholding_amt=330, net_amt=9670,
        holder_name="김작가", bank="국민", account_no_masked="******1234",
        requested_at=NOW,
    )


# ── 계좌 등록 검증 ────────────────────────────────────
async def test_set_bank_account_rejects_blank_holder_or_bank():
    svc = PayoutService(FakePayoutRepository())
    with pytest.raises(ValidationError):
        await svc.set_bank_account(uuid.uuid4(), "  ", "국민", "1234567890")
    with pytest.raises(ValidationError):
        await svc.set_bank_account(uuid.uuid4(), "김작가", "  ", "1234567890")


async def test_set_bank_account_rejects_non_digit_number():
    svc = PayoutService(FakePayoutRepository())
    with pytest.raises(ValidationError):
        await svc.set_bank_account(uuid.uuid4(), "김작가", "국민", "12ab567890")


async def test_set_bank_account_rejects_too_short_or_too_long():
    svc = PayoutService(FakePayoutRepository())
    with pytest.raises(ValidationError):
        await svc.set_bank_account(uuid.uuid4(), "김작가", "국민", "123")  # 6자리 미만
    with pytest.raises(ValidationError):
        await svc.set_bank_account(uuid.uuid4(), "김작가", "국민", "1" * 21)  # 20자리 초과


async def test_set_bank_account_strips_dashes_and_masks():
    repo = FakePayoutRepository()
    svc = PayoutService(repo)
    account_id = uuid.uuid4()

    view = await svc.set_bank_account(account_id, "김작가", "국민", "123-456-7890")

    assert view.account_no_masked == "******7890"
    assert repo.accounts[account_id] is view


async def test_set_bank_account_encrypts_account_number():
    repo = FakePayoutRepository()
    svc = PayoutService(repo)
    account_id = uuid.uuid4()

    await svc.set_bank_account(account_id, "김작가", "국민", "1234567890")

    stored_enc = repo.account_no_enc[account_id]
    assert stored_enc != "1234567890"  # 평문 그대로 저장 안 됨
    assert decrypt(stored_enc) == "1234567890"  # 복호화하면 원문


async def test_get_bank_account_returns_none_when_unset():
    svc = PayoutService(FakePayoutRepository())
    assert await svc.get_bank_account(uuid.uuid4()) is None


# ── 출금 신청 ─────────────────────────────────────────
async def test_request_payout_raises_no_bank_account():
    repo = FakePayoutRepository()
    repo.seed_payable(uuid.uuid4(), PayableSummary(gross_amt=1000, withholding_amt=33, net_amt=967, order_count=1))
    svc = PayoutService(repo)

    with pytest.raises(NoBankAccount):
        await svc.request_payout(uuid.uuid4())  # 계좌 미등록


async def test_request_payout_raises_nothing_to_payout_when_no_settlement():
    repo = FakePayoutRepository()
    svc = PayoutService(repo)
    author_id = uuid.uuid4()
    await svc.set_bank_account(author_id, "김작가", "국민", "1234567890")

    with pytest.raises(NothingToPayout):
        await svc.request_payout(author_id)  # payable 미등록(잔액 0)


async def test_request_payout_success_returns_view():
    repo = FakePayoutRepository()
    svc = PayoutService(repo)
    author_id = uuid.uuid4()
    await svc.set_bank_account(author_id, "김작가", "국민", "1234567890")
    repo.seed_payable(author_id, PayableSummary(gross_amt=10000, withholding_amt=330, net_amt=9670, order_count=2))

    payout = await svc.request_payout(author_id)

    assert payout.status == REQUESTED
    assert payout.net_amt == 9670
    assert (await svc.list_payouts(author_id)) == [payout]


# ── 운영자 상태전이 ───────────────────────────────────
async def test_approve_success_from_requested():
    repo = FakePayoutRepository()
    p = _payout(uuid.uuid4(), status=REQUESTED)
    repo.seed_payout(p)
    svc = PayoutService(repo)

    await svc.approve(p.id, operator_id=uuid.uuid4())

    assert repo.payouts[p.id].status == APPROVED


async def test_approve_raises_not_found_for_missing_payout():
    svc = PayoutService(FakePayoutRepository())
    with pytest.raises(PayoutNotFound):
        await svc.approve(uuid.uuid4(), operator_id=uuid.uuid4())


async def test_approve_raises_invalid_state_when_already_approved():
    repo = FakePayoutRepository()
    p = _payout(uuid.uuid4(), status=APPROVED)
    repo.seed_payout(p)
    svc = PayoutService(repo)

    with pytest.raises(InvalidPayoutState):
        await svc.approve(p.id, operator_id=uuid.uuid4())


async def test_mark_paid_success_from_approved():
    repo = FakePayoutRepository()
    p = _payout(uuid.uuid4(), status=APPROVED)
    repo.seed_payout(p)
    svc = PayoutService(repo)

    await svc.mark_paid(p.id, operator_id=uuid.uuid4(), memo="이체완료")

    assert repo.payouts[p.id].status == PAID
    assert repo.payouts[p.id].memo == "이체완료"


async def test_mark_paid_raises_invalid_state_when_not_approved():
    repo = FakePayoutRepository()
    p = _payout(uuid.uuid4(), status=REQUESTED)  # 승인 전
    repo.seed_payout(p)
    svc = PayoutService(repo)

    with pytest.raises(InvalidPayoutState):
        await svc.mark_paid(p.id, operator_id=uuid.uuid4())


async def test_reject_success_from_requested_or_approved():
    repo = FakePayoutRepository()
    p1, p2 = _payout(uuid.uuid4(), status=REQUESTED), _payout(uuid.uuid4(), status=APPROVED)
    repo.seed_payout(p1)
    repo.seed_payout(p2)
    svc = PayoutService(repo)

    await svc.reject(p1.id, operator_id=uuid.uuid4(), memo="계좌 확인 불가")
    await svc.reject(p2.id, operator_id=uuid.uuid4())

    assert repo.payouts[p1.id].status == REJECTED
    assert repo.payouts[p2.id].status == REJECTED


async def test_reject_raises_invalid_state_when_already_paid():
    repo = FakePayoutRepository()
    p = _payout(uuid.uuid4(), status=PAID)
    repo.seed_payout(p)
    svc = PayoutService(repo)

    with pytest.raises(InvalidPayoutState):
        await svc.reject(p.id, operator_id=uuid.uuid4())


# ── report_hook(woncheon 원천징수 신고 커넥터, lr-ac61f505) 연동 ─────
class _FakeReportHook:
    """PayoutReportHook 구현 — 호출 여부/인자만 기록(woncheon 구체 구현은 모름)."""
    def __init__(self, raise_error: bool = False):
        self.raise_error = raise_error
        self.called_with: list = []

    async def on_paid(self, payout_id):
        self.called_with.append(payout_id)
        if self.raise_error:
            raise RuntimeError("woncheon 신고 실패 시뮬레이션")


async def test_mark_paid_calls_report_hook_on_success():
    repo = FakePayoutRepository()
    p = _payout(uuid.uuid4(), status=APPROVED)
    repo.seed_payout(p)
    hook = _FakeReportHook()
    svc = PayoutService(repo, report_hook=hook)

    await svc.mark_paid(p.id, operator_id=uuid.uuid4())

    assert repo.payouts[p.id].status == PAID
    assert hook.called_with == [p.id]


async def test_mark_paid_swallows_report_hook_exception_and_keeps_paid():
    """신고 훅이 실패해도 지급 자체(PAID 전이)는 막지 않는다 — best-effort 핵심 불변식."""
    repo = FakePayoutRepository()
    p = _payout(uuid.uuid4(), status=APPROVED)
    repo.seed_payout(p)
    hook = _FakeReportHook(raise_error=True)
    svc = PayoutService(repo, report_hook=hook)

    await svc.mark_paid(p.id, operator_id=uuid.uuid4())  # 예외가 여기로 전파되면 실패

    assert repo.payouts[p.id].status == PAID  # 훅 실패와 무관하게 유지
    assert hook.called_with == [p.id]


async def test_mark_paid_without_report_hook_still_works():
    """report_hook 미주입(기본 None) — 기존 동작(하위호환) 그대로."""
    repo = FakePayoutRepository()
    p = _payout(uuid.uuid4(), status=APPROVED)
    repo.seed_payout(p)
    svc = PayoutService(repo)  # report_hook 생략

    await svc.mark_paid(p.id, operator_id=uuid.uuid4())

    assert repo.payouts[p.id].status == PAID


async def test_mark_paid_does_not_call_hook_when_transition_fails():
    """상태전이 자체가 실패(REQUESTED에서 바로 PAID)하면 훅은 아예 호출되지 않는다."""
    repo = FakePayoutRepository()
    p = _payout(uuid.uuid4(), status=REQUESTED)  # 승인 전
    repo.seed_payout(p)
    hook = _FakeReportHook()
    svc = PayoutService(repo, report_hook=hook)

    with pytest.raises(InvalidPayoutState):
        await svc.mark_paid(p.id, operator_id=uuid.uuid4())

    assert hook.called_with == []
