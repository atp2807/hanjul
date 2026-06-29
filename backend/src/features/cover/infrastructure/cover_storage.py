"""표지 업로드 저장 — 로컬 디스크 어댑터 (CoverStorage 포트 구현).

업로드 디렉토리에 저장하고, 앱이 /uploads 로 정적 서빙 → 공개 URL 반환.
나중에 S3 등으로 교체 시 이 어댑터만 갈아끼우면 됨.
"""
import uuid
from pathlib import Path


class LocalDiskCoverStorage:
    def __init__(self, base_dir: str, public_url: str):
        self.dir = Path(base_dir) / "covers"
        self.public_url = public_url.rstrip("/")

    async def save(self, data: bytes, ext: str) -> str:
        self.dir.mkdir(parents=True, exist_ok=True)
        name = f"{uuid.uuid4().hex}.{ext}"
        (self.dir / name).write_bytes(data)
        return f"{self.public_url}/uploads/covers/{name}"
