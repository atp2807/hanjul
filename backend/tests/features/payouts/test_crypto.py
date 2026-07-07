"""payouts.crypto 단위 — 암복호화 라운드트립 + 폴백키 + 마스킹."""
import pytest
from cryptography.fernet import InvalidToken
from src.config.settings import settings
from src.features.payouts.application.crypto import decrypt, encrypt, mask_account


# ── 암복호화 라운드트립 ───────────────────────────────
async def test_encrypt_decrypt_roundtrip():
    token = encrypt("110123456789")
    assert decrypt(token) == "110123456789"


async def test_encrypt_output_is_not_plaintext():
    token = encrypt("110123456789")
    assert token != "110123456789"


async def test_decrypt_corrupted_token_raises_invalid_token():
    token = encrypt("110123456789")
    tampered_char = "B" if not token.startswith("B") else "C"
    tampered = tampered_char + token[1:]
    with pytest.raises(InvalidToken):
        decrypt(tampered)


# ── SETTLEMENT_ENC_KEY 미설정 시 폴백(JWT 시크릿 파생) ─
async def test_fallback_roundtrip_when_settlement_key_unset(monkeypatch):
    monkeypatch.setattr(settings, "SETTLEMENT_ENC_KEY", "")
    monkeypatch.setattr(settings, "JWT_SECRET_KEY", "fallback-secret-a")

    token = encrypt("998877665544")

    assert decrypt(token) == "998877665544"


async def test_fallback_key_is_derived_from_jwt_secret(monkeypatch):
    """폴백키는 JWT_SECRET_KEY 로부터 파생 — 시크릿이 바뀌면 이전 토큰을 복호 못함."""
    monkeypatch.setattr(settings, "SETTLEMENT_ENC_KEY", "")
    monkeypatch.setattr(settings, "JWT_SECRET_KEY", "fallback-secret-a")
    token = encrypt("998877665544")

    monkeypatch.setattr(settings, "JWT_SECRET_KEY", "fallback-secret-b")

    with pytest.raises(InvalidToken):
        decrypt(token)


# ── 마스킹 ────────────────────────────────────────────
async def test_mask_account_keeps_last_four_digits():
    assert mask_account("110123456789") == "********6789"


async def test_mask_account_masks_entirely_when_four_or_fewer():
    assert mask_account("1234") == "****"
    assert mask_account("12") == "**"
