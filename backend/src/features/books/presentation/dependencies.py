"""books 표현 레이어 의존성 — 서비스 조립 (DI 합성 루트)."""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import get_session
from src.config.settings import settings
from src.features.accounts.application.account_service import AccountService
from src.features.accounts.infrastructure.account_repo import SqlAccountRepository
from src.features.books.application.book_service import BookService
from src.features.books.application.content_rating_service import ContentRatingService
from src.features.books.infrastructure.anthropic_rating_classifier import build_rating_classifier
from src.features.books.infrastructure.book_repo import SqlBookRepository


def get_book_service(session: AsyncSession = Depends(get_session)) -> BookService:
    return BookService(
        SqlBookRepository(session),
        account_tier=AccountService(SqlAccountRepository(session)),
    )


def get_content_rating_service(
    session: AsyncSession = Depends(get_session),
) -> ContentRatingService:
    return ContentRatingService(
        SqlBookRepository(session), build_rating_classifier(settings)
    )
