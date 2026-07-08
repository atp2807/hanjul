"""신분증 사진 저장 — 비공개 로컬 디스크 어댑터. ⚠️ PII 전용, 절대 공개 서빙 경로에 두지 않는다.

cover_storage.py(LocalDiskCoverStorage)와 달리 공개 URL을 만들지 않는다 — 접근은 반드시
potato 운영자 전용 엔드포인트(GET /potato/age-verification/{id}/photo)가 매 요청마다
인증·상태(PENDING인지)를 확인한 뒤 바이트를 직접 읽어 응답하는 방식으로만 이뤄진다.
저장 루트(settings.AGE_VERIFICATION_DIR)는 반드시 UPLOAD_DIR(=/uploads 정적서빙 마운트)
바깥이어야 한다 — main.py가 app.mount("/uploads", ...)로 그 하위 전체를 공개하기 때문.

심사 완료(승인/거부) 시 서비스가 delete()를 호출해 원본을 즉시 지운다(목적 외 보관 금지).
"""
import asyncio
import uuid
from pathlib import Path


def _is_safe_key(key: str) -> bool:
    """key는 순수 basename(uuid4hex+ext) — 경로 조작('..', '/', 절대경로) 차단."""
    if not key or key != Path(key).name:
        return False
    return not (".." in key or "/" in key or "\\" in key)


class LocalDiskIdPhotoStorage:
    def __init__(self, root_dir: str):
        self._root = Path(root_dir)
        self._root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path | None:
        if not _is_safe_key(key):
            return None
        return self._root / key

    async def save(self, data: bytes, ext: str) -> str:
        key = f"{uuid.uuid4().hex}.{ext}"
        path = self._root / key
        await asyncio.get_event_loop().run_in_executor(None, path.write_bytes, data)
        return key

    async def get(self, key: str) -> bytes | None:
        path = self._path(key)
        if path is None or not path.is_file():
            return None
        return await asyncio.get_event_loop().run_in_executor(None, path.read_bytes)

    async def delete(self, key: str) -> None:
        """원본 삭제(심사 목적 외 보관 금지). 호출자가 실패를 catch해 로그만 남기고 진행한다."""
        path = self._path(key)
        if path is None:
            raise ValueError(f"unsafe storage key: {key!r}")
        await asyncio.get_event_loop().run_in_executor(None, path.unlink, True)  # missing_ok=True
