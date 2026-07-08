"""OrderConfirmationEmailHook — 결제확인 best-effort 훅 (Fake account/book + 발송기록).

FakeEmailSender 는 이 파일에서만 쓰는 대역이라 test_payout_service.py의 _FakeReportHook
관례(fixtures 아닌 테스트 내 정의)를 따른다.
"""
import uuid

from src.features.accounts.application.account_service import AccountService
from src.features.accounts.domain.models import AccountProfile
from src.features.books.application.book_service import BookService
from src.features.email.domain.models import EmailMessage
from src.features.email.infrastructure.order_hook import OrderConfirmationEmailHook

from tests.fixtures.fake_accounts_repo import FakeAccountsRepository
from tests.fixtures.fake_book_repo import FakeBookRepository


class FakeEmailSender:
    """발송 기록만 남기는 대역 — SMTP/데모 구현은 모른다."""

    def __init__(self) -> None:
        self.sent: list[EmailMessage] = []

    async def send(self, message: EmailMessage) -> None:
        self.sent.append(message)


async def _hook_with(email: str | None, title: str = "한줄 첫 책"):
    accounts_repo = FakeAccountsRepository()
    buyer_id = uuid.uuid4()
    accounts_repo.seed(
        AccountProfile(id=buyer_id, email=email, display_name="독자", role="READER", bio=None)
    )
    accounts = AccountService(accounts_repo)

    book_repo = FakeBookRepository()
    book_id = await book_repo.create_book(title=title, kind="BOOK", language="ko")
    books = BookService(book_repo)

    sender = FakeEmailSender()
    hook = OrderConfirmationEmailHook(sender, accounts, books)
    return hook, sender, buyer_id, book_id


async def test_order_paid_sends_confirmation_email():
    hook, sender, buyer_id, book_id = await _hook_with(email="reader@x.com", title="바이브코딩 첫걸음")

    await hook.order_paid(buyer_id, book_id, 12000)

    assert len(sender.sent) == 1
    msg = sender.sent[0]
    assert msg.to == "reader@x.com"
    assert "바이브코딩 첫걸음" in msg.subject
    assert "12,000" in msg.html


async def test_order_paid_skips_send_when_no_email():
    """탈퇴 등으로 email 이 None 이면 조용히 스킵 — send 0회."""
    hook, sender, buyer_id, book_id = await _hook_with(email=None)

    await hook.order_paid(buyer_id, book_id, 5000)

    assert sender.sent == []
