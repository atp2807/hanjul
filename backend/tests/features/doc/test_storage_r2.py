"""R2Storage 단위 테스트 — boto3 client 를 스텁으로 교체(실 네트워크 없음). (juldoc 이식)

put/get/exists/url_for 의 로직(prefix 부여, run_in_executor 논블로킹, 공개/내부 URL)만 검증.
juldoc 대비: 오브젝트 prefix 가 hanjul/media (juldoc/media 아님).
"""
import pytest
from botocore.exceptions import ClientError

import src.features.doc.infrastructure.storage_r2 as r2mod
from src.features.doc.infrastructure.storage_r2 import R2Storage


class FakeS3:
    """put/get/head_object 를 인메모리 dict 로 흉내. fail_* 지정 시 ClientError 를 던진다."""

    def __init__(self):
        self.objects: dict[str, dict] = {}
        self.put_calls: list[dict] = []
        self.fail_get: str | None = None
        self.fail_put: str | None = None
        self.fail_head: str | None = None

    def put_object(self, *, Bucket, Key, Body, ContentType):
        if self.fail_put is not None:
            raise ClientError({"Error": {"Code": self.fail_put}}, "PutObject")
        self.put_calls.append(
            {"Bucket": Bucket, "Key": Key, "Body": Body, "ContentType": ContentType}
        )
        self.objects[Key] = {"Body": Body, "ContentType": ContentType}

    def get_object(self, *, Bucket, Key):
        if self.fail_get is not None:
            raise ClientError({"Error": {"Code": self.fail_get}}, "GetObject")
        if Key not in self.objects:
            raise ClientError({"Error": {"Code": "NoSuchKey"}}, "GetObject")

        class _Body:
            def __init__(self, data):
                self._data = data

            def read(self):
                return self._data

        return {"Body": _Body(self.objects[Key]["Body"])}

    def head_object(self, *, Bucket, Key):
        if self.fail_head is not None:
            raise ClientError({"Error": {"Code": self.fail_head}}, "HeadObject")
        if Key not in self.objects:
            raise ClientError({"Error": {"Code": "404"}}, "HeadObject")
        return {}


@pytest.fixture
def fake_s3(monkeypatch) -> FakeS3:
    fake = FakeS3()
    monkeypatch.setattr(r2mod.boto3, "client", lambda *a, **k: fake)
    return fake


def _storage(public_url: str = "") -> R2Storage:
    return R2Storage(
        endpoint_url="https://acct.r2.cloudflarestorage.com",
        access_key_id="ak",
        secret_access_key="sk",
        bucket_name="hanjul-media",
        public_url=public_url,
    )


class TestPut:
    async def test_put_applies_prefix_and_content_type(self, fake_s3):
        storage = _storage()
        await storage.put("abc.png", b"IMG", "image/png")
        assert len(fake_s3.put_calls) == 1
        call = fake_s3.put_calls[0]
        assert call["Key"] == "hanjul/media/abc.png"  # prefix 자동 부여
        assert call["Body"] == b"IMG"
        assert call["ContentType"] == "image/png"
        assert call["Bucket"] == "hanjul-media"

    async def test_get_roundtrip(self, fake_s3):
        storage = _storage()
        await storage.put("k.png", b"BYTES", "image/png")
        assert await storage.get("k.png") == b"BYTES"

    async def test_get_missing_returns_none(self, fake_s3):
        assert await _storage().get("missing.png") is None

    async def test_exists(self, fake_s3):
        storage = _storage()
        await storage.put("k.png", b"X", "image/png")
        assert await storage.exists("k.png") is True
        assert await storage.exists("nope.png") is False


class TestUrlFor:
    def test_public_url_when_configured(self, fake_s3):
        storage = _storage(public_url="https://cdn.hanjul.dev")
        assert storage.url_for("abc.png") == "https://cdn.hanjul.dev/hanjul/media/abc.png"

    def test_internal_url_fallback(self, fake_s3):
        assert _storage().url_for("abc.png") == (
            "https://acct.r2.cloudflarestorage.com/hanjul-media/hanjul/media/abc.png"
        )

    def test_url_is_absolute_for_redirect_branch(self, fake_s3):
        assert "://" in _storage().url_for("abc.png")


class TestErrorLogging:
    """오설정(AccessDenied/NoSuchBucket 등)을 삼키지 않고 진단 가능하게 남기는지."""

    async def test_get_nosuchkey_is_quiet(self, fake_s3, caplog):
        with caplog.at_level("WARNING", logger="storage.r2"):
            assert await _storage().get("missing.png") is None
        assert caplog.records == []

    async def test_get_access_denied_logs_and_returns_none(self, fake_s3, caplog):
        fake_s3.fail_get = "AccessDenied"
        with caplog.at_level("WARNING", logger="storage.r2"):
            assert await _storage().get("k.png") is None
        assert any("AccessDenied" in r.getMessage() for r in caplog.records)

    async def test_exists_404_is_quiet(self, fake_s3, caplog):
        with caplog.at_level("WARNING", logger="storage.r2"):
            assert await _storage().exists("missing.png") is False
        assert caplog.records == []

    async def test_exists_nosuchbucket_logs_and_returns_false(self, fake_s3, caplog):
        fake_s3.fail_head = "NoSuchBucket"
        with caplog.at_level("WARNING", logger="storage.r2"):
            assert await _storage().exists("k.png") is False
        assert any("NoSuchBucket" in r.getMessage() for r in caplog.records)

    async def test_put_client_error_logs_and_reraises(self, fake_s3, caplog):
        fake_s3.fail_put = "SignatureDoesNotMatch"
        with caplog.at_level("ERROR", logger="storage.r2"):
            with pytest.raises(ClientError):
                await _storage().put("k.png", b"X", "image/png")
        assert any("SignatureDoesNotMatch" in r.getMessage() for r in caplog.records)
