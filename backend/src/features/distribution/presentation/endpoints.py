"""서점 배포 API — 출판본을 EPUB+ONIX로 만들어 채널 전송 + 이력."""
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import get_session
from src.config.settings import settings
from src.engine.publishing.epub import EpubBook, EpubChapter, build_epub
from src.engine.publishing.onix import OnixProduct, build_onix
from src.features.accounts.application.account_service import AccountService
from src.features.accounts.presentation.dependencies import get_account_service
from src.features.books.application.book_service import BookService
from src.features.books.domain.models import BookNotFound
from src.features.books.presentation.dependencies import get_book_service
from src.features.catalog.application.catalog_service import CatalogService
from src.features.catalog.domain.models import BookNotFound as CatalogBookNotFound
from src.features.catalog.presentation.dependencies import get_catalog_service
from src.features.distribution.application.distribution_service import DistributionService
from src.features.distribution.domain.models import UnknownChannel
from src.features.distribution.infrastructure.channels import build_channel
from src.features.distribution.infrastructure.distribution_repo import SqlDistributionRepository
from src.features.distribution.presentation.schemas import DistributeRequest, DistributionResponse

router = APIRouter(tags=["distribution"])


@router.post("/books/{book_id}/distribute", response_model=DistributionResponse, status_code=201)
async def distribute(
    book_id: UUID,
    body: DistributeRequest,
    book_svc: BookService = Depends(get_book_service),
    catalog_svc: CatalogService = Depends(get_catalog_service),
    acct: AccountService = Depends(get_account_service),
    session: AsyncSession = Depends(get_session),
) -> DistributionResponse:
    try:
        content = await book_svc.get_content(book_id)
        meta = await catalog_svc.get_meta(book_id)
    except (BookNotFound, CatalogBookNotFound):
        raise HTTPException(404, "book not found")
    if meta.status != "PUBLISHED":
        raise HTTPException(409, "출판본만 서점 배포 가능")

    author = None
    if meta.author_id:
        names = await acct.names_for([meta.author_id])
        author = names.get(meta.author_id)

    modified = datetime.now(timezone.utc)
    epub = build_epub(
        EpubBook(
            title=content.title,
            language=content.language,
            identifier=(f"urn:isbn:{meta.isbn}" if meta.isbn else f"urn:uuid:{book_id}"),
            author=author,
            chapters=[EpubChapter(title=ch.title, html="\n".join(b.html for b in ch.blocks)) for ch in content.chapters],
        ),
        modified.strftime("%Y-%m-%dT%H:%M:%SZ"),
    )
    onix = build_onix(
        OnixProduct(
            record_reference=str(book_id), title=meta.title, language=meta.language,
            isbn=meta.isbn, author=author, price_amt=meta.price_amt,
        ),
        modified.strftime("%Y%m%d"),
    )

    try:
        channel = build_channel(body.channel.upper(), settings)
    except UnknownChannel:
        raise HTTPException(400, "배포 채널 미설정 (DISTRIBUTION_DEMO 또는 SFTP 설정 필요)")

    svc = DistributionService(SqlDistributionRepository(session), channel)
    result = await svc.distribute(book_id, epub, onix, filename=str(book_id))
    return DistributionResponse.model_validate(result)


@router.get("/books/{book_id}/distributions", response_model=list[DistributionResponse])
async def distributions(
    book_id: UUID, session: AsyncSession = Depends(get_session)
) -> list[DistributionResponse]:
    rows = await SqlDistributionRepository(session).list_for_book(book_id)
    return [DistributionResponse.model_validate(d) for d in rows]
