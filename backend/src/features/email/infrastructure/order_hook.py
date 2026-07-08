"""billing.domain.models.OrderEmailHook 구현 — 결제확인 후 best-effort 구매확인 메일.

billing 피처는 이 구현을 모른다(Protocol만 안다) — DI(billing/presentation/dependencies.py)가
이 구현을 조립해 주입한다. woncheon 의 WoncheonPayoutReportHook(payout_hook.py)과 동형 패턴.
"""
import logging
from uuid import UUID

from src.features.accounts.application.account_service import AccountService
from src.features.books.application.book_service import BookService
from src.features.email.domain.models import order_confirmation_email
from src.features.email.domain.ports import EmailSender

logger = logging.getLogger(__name__)


class OrderConfirmationEmailHook:
    def __init__(self, email_sender: EmailSender, accounts: AccountService, books: BookService):
        self._email_sender = email_sender
        self._accounts = accounts
        self._books = books

    async def order_paid(self, buyer_id: UUID, book_id: UUID, amount: int) -> None:
        profile = await self._accounts.get_profile(buyer_id)
        if not profile.email:
            return  # 탈퇴 등으로 이메일 없음 — 조용히 스킵(호출부가 best-effort로 감쌈)
        # account_id=buyer_id 로 넘겨야 연령 게이트(dc-daeb0d3d)가 구매자의 실제 인증등급으로
        # 판정한다(익명 취급 시 "ALL"로 굳어 등급 있는 책은 늘 막힘 — 이미 구매 완료한 책인데도).
        book = await self._books.get_content(book_id, account_id=buyer_id)
        message = order_confirmation_email(profile.email, book.title, amount)
        await self._email_sender.send(message)
