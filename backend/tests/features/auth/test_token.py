"""JWT 발급/검증 라운드트립."""
import uuid

from src.features.auth.application.token import JwtTokenIssuer


def test_issue_and_verify_roundtrip():
    issuer = JwtTokenIssuer("s3cret", "HS256", 1)
    account_id = uuid.uuid4()
    token = issuer.issue(account_id, "AUTHOR")
    payload = issuer.verify(token)
    assert payload["sub"] == str(account_id)
    assert payload["role"] == "AUTHOR"
    assert "exp" in payload
