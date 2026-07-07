"""메타 테스트 — Alembic 마이그레이션 head가 정확히 1개인지 (DB 연결 없이).

브랜치를 나눠 작업하다 리베이스를 놓치면 down_revision이 갈라져 head가 여러 개가
될 수 있다. 그러면 ``alembic upgrade head``의 적용 순서가 모호해진다. 스크립트
디렉토리만 파싱하면 되므로 DB 연결이나 실제 DB 상태 없이 조기에 잡을 수 있다.
"""
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent


def test_alembic_has_single_head():
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    script = ScriptDirectory.from_config(config)

    heads = script.get_heads()

    assert len(heads) == 1, (
        f"Alembic head가 {len(heads)}개({heads})임 — 마이그레이션 브랜치 분기 확인 필요. "
        "down_revision 체인이 두 갈래로 나뉜 리비전을 찾아 하나를 다른 하나 뒤로 재배치할 것."
    )
