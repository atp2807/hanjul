"""계좌번호 등 금융 민감정보 대칭 암호화 (Fernet = AES128-CBC + HMAC).

키 = settings.SETTLEMENT_ENC_KEY(base64 32B). 비면 dev용 임시키를 JWT 시크릿에서 파생
(운영은 반드시 SETTLEMENT_ENC_KEY 주입 — 미주입 시 재시작마다 키 바뀌어 복호 불가).
"""
import base64
import hashlib

from cryptography.fernet import Fernet

from src.config.settings import settings


def _fernet() -> Fernet:
    key = settings.SETTLEMENT_ENC_KEY
    if not key:
        # dev 폴백 — JWT 시크릿에서 32B 파생(운영 미주입 방지용, 안정적이나 운영엔 별도키 권장)
        digest = hashlib.sha256(settings.JWT_SECRET_KEY.encode()).digest()
        key = base64.urlsafe_b64encode(digest).decode()
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt(token: str) -> str:
    return _fernet().decrypt(token.encode()).decode()


def mask_account(account_no: str) -> str:
    """조회 노출용 마스킹 — 뒷 4자리만."""
    if len(account_no) <= 4:
        return "*" * len(account_no)
    return "*" * (len(account_no) - 4) + account_no[-4:]
