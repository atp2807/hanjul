"""로컬 파일시스템 저장 어댑터 — R2 미설정(개발/폴백)일 때 사용. (juldoc storage/local 이식)

파일을 root/{key} 로 저장하고, url_for 는 상대경로 '/media/{key}' 를 돌려준다.
서빙은 GET /api/media/{key} 엔드포인트가 get() 으로 바이트를 읽어 프록시한다.
"""
import asyncio
from pathlib import Path

from src.features.doc.domain.storage import StorageAdapter


def _is_safe_key(key: str) -> bool:
    """content-addressed key 는 순수 basename(sha256hex+ext) — 경로 조작 차단.

    '/', '\\', '..', 절대경로를 거부해 root 밖으로 못 나가게 한다.
    """
    if not key or key != Path(key).name:
        return False
    return not (".." in key or "/" in key or "\\" in key)


class LocalStorage(StorageAdapter):
    def __init__(self, root: Path) -> None:
        self._root = Path(root)
        self._root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path | None:
        if not _is_safe_key(key):
            return None
        return self._root / key

    async def put(self, key: str, data: bytes, content_type: str) -> None:
        path = self._path(key)
        if path is None:
            raise ValueError(f"unsafe storage key: {key!r}")
        # content-addressed: 같은 key = 같은 바이트. 동기 파일 쓰기를 executor 로 오프로드.
        await asyncio.get_event_loop().run_in_executor(None, path.write_bytes, data)

    async def get(self, key: str) -> bytes | None:
        path = self._path(key)
        if path is None or not path.is_file():
            return None
        return await asyncio.get_event_loop().run_in_executor(None, path.read_bytes)

    def url_for(self, key: str) -> str:
        return f"/media/{key}"

    async def exists(self, key: str) -> bool:
        path = self._path(key)
        return path is not None and path.is_file()
