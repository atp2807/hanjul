"""build_email_sender — EMAIL_DEMO/SMTP_HOST 조합에 따라 Demo↔Smtp 선택 (woncheon
build_woncheon_adapter 테스트 관례처럼 class 속성 Fake settings 사용)."""
from src.features.email.infrastructure.email_sender import (
    DemoEmailSender,
    SmtpEmailSender,
    build_email_sender,
)


class _FakeSettings:
    EMAIL_DEMO = False
    SMTP_HOST = ""
    SMTP_PORT = 587
    SMTP_USER = ""
    SMTP_PASSWORD = ""
    EMAIL_FROM = "한줄 <no-reply@hanjul.io>"


def test_demo_when_email_demo_true_even_with_smtp_configured():
    class S(_FakeSettings):
        EMAIL_DEMO = True
        SMTP_HOST = "smtp.example.com"

    assert isinstance(build_email_sender(S()), DemoEmailSender)


def test_demo_when_smtp_host_unset():
    assert isinstance(build_email_sender(_FakeSettings()), DemoEmailSender)  # EMAIL_DEMO=False지만 SMTP_HOST=""


def test_smtp_when_demo_false_and_host_configured():
    class S(_FakeSettings):
        SMTP_HOST = "smtp.example.com"
        SMTP_USER = "user"
        SMTP_PASSWORD = "pw"

    sender = build_email_sender(S())

    assert isinstance(sender, SmtpEmailSender)
    assert sender._host == "smtp.example.com"
