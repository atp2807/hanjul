"""운영자 비밀번호 해시 — stdlib pbkdf2_hmac (외부 의존성 0).

내부 운영자 소수에 충분. 형식: `pbkdf2_sha256$iterations$salt_b64$hash_b64`.
운영자 외 일반 사용자 인증은 소셜 OAuth(auth 피처)이므로 비번 해시는 여기서만 쓴다.
"""
import base64
import hashlib
import hmac
import os

_ALGO = "pbkdf2_sha256"
_ITERATIONS = 600_000  # OWASP 권고선(pbkdf2-sha256)
_SALT_BYTES = 16


def hash_password(password: str) -> str:
    salt = os.urandom(_SALT_BYTES)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _ITERATIONS)
    return f"{_ALGO}${_ITERATIONS}${base64.b64encode(salt).decode()}${base64.b64encode(dk).decode()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algo, iterations, salt_b64, hash_b64 = encoded.split("$")
        if algo != _ALGO:
            return False
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(hash_b64)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, int(iterations))
        return hmac.compare_digest(dk, expected)
    except Exception:
        return False
