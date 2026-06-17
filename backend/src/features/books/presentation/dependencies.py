"""books 표현 레이어 의존성 — 서비스 조립 (DI 합성 루트)."""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import get_session
from src.features.books.application.book_service import BookService
from src.features.books.infrastructure.book_repo import SqlBookRepository


def get_book_service(session: AsyncSession = Depends(get_session)) -> BookService:
    return BookService(SqlBookRepository(session))
