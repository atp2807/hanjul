"""이메일 발송 포트 — SMTP/데모 등 구체 구현을 감춘다."""
from typing import Protocol

from src.features.email.domain.models import EmailMessage


class EmailSender(Protocol):
    async def send(self, message: EmailMessage) -> None:
        """이메일 한 통 발송. 실패 시 예외를 던진다 — 호출부(각 훅)가 best-effort로 감싼다."""
        ...
