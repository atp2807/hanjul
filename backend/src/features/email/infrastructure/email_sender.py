"""이메일 발송 어댑터 — SMTP(aiosmtplib) 실구현 + 데모 폴백.

cover 피처(build_cover_generator, novelpotato_generator.py:50-54)와 동일한 데모게이트
패턴: 설정에 따라 Demo↔실구현을 고른다. 단, 이메일은 각 피처의 best-effort 훅에서만
호출되므로(실패해도 결제/지급 흐름을 막지 않음) SMTP 미설정 시에도 에러 대신 Demo로
조용히 폴백한다 — cover/woncheon("설정 없으면 명시적 에러")과는 이 지점만 다르다.
"""
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import aiosmtplib

from src.features.email.domain.models import EmailMessage

logger = logging.getLogger(__name__)


class DemoEmailSender:
    """데모 — 실제 발송 없이 로그만 남긴다 (dev/E2E, SMTP 미설정 시 안전한 폴백)."""

    async def send(self, message: EmailMessage) -> None:
        logger.info("[EMAIL:demo] to=%s subject=%s", message.to, message.subject)


class SmtpEmailSender:
    """라이브 — aiosmtplib로 STARTTLS 발송."""

    def __init__(self, host: str, port: int, user: str, password: str, sender: str):
        self._host = host
        self._port = port
        self._user = user
        self._password = password
        self._from = sender

    async def send(self, message: EmailMessage) -> None:
        if not self._host:
            raise RuntimeError("SMTP_HOST 미설정 — 이메일 발송 비활성")
        mime = MIMEMultipart("alternative")
        mime["Subject"] = message.subject
        mime["From"] = self._from
        mime["To"] = message.to
        mime.attach(MIMEText(message.text, "plain", "utf-8"))
        mime.attach(MIMEText(message.html, "html", "utf-8"))
        await aiosmtplib.send(
            mime,
            hostname=self._host,
            port=self._port,
            username=self._user or None,
            password=self._password or None,
            start_tls=True,
        )


def build_email_sender(settings):
    """EMAIL_DEMO 거나 SMTP_HOST 미설정이면 데모, 아니면 SMTP 라이브."""
    if settings.EMAIL_DEMO or not settings.SMTP_HOST:
        return DemoEmailSender()
    return SmtpEmailSender(
        settings.SMTP_HOST,
        settings.SMTP_PORT,
        settings.SMTP_USER,
        settings.SMTP_PASSWORD,
        settings.EMAIL_FROM,
    )
