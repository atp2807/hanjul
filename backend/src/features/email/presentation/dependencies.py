"""email 표현 레이어 DI — email_sender 조립 + 타 피처 훅 composition root.

build_order_email_hook 은 billing/presentation/dependencies.py(get_order_service)가 FastAPI
Depends 캐시 밖에서 같은 session 으로 서비스를 조립하기 위해 함수 형태로 노출한다
(woncheon build_payout_report_hook, woncheon/presentation/dependencies.py:24-27 과 동형).
"""
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import settings as _settings
from src.features.accounts.application.account_service import AccountService
from src.features.accounts.infrastructure.account_repo import SqlAccountRepository
from src.features.billing.domain.models import OrderEmailHook
from src.features.books.application.book_service import BookService
from src.features.books.infrastructure.book_repo import SqlBookRepository
from src.features.email.domain.ports import EmailSender
from src.features.email.infrastructure.email_sender import build_email_sender
from src.features.email.infrastructure.order_hook import OrderConfirmationEmailHook


def get_email_sender() -> EmailSender:
    return build_email_sender(_settings)


def build_order_email_hook(session: AsyncSession) -> OrderEmailHook:
    accounts = AccountService(SqlAccountRepository(session))
    books = BookService(SqlBookRepository(session), account_tier=accounts)
    return OrderConfirmationEmailHook(get_email_sender(), accounts, books)
