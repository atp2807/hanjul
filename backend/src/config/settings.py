"""애플리케이션 설정 (pydantic-settings).

haedream 컨벤션을 따르되, MVP 단계라 RDS/SSL/멀티엔진 설정은 생략.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── DB ──────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://hanjul:hanjul@localhost:5432/hanjul"
    DATABASE_POOL_SIZE: int = 5
    DATABASE_MAX_OVERFLOW: int = 10
    DATABASE_POOL_TIMEOUT: int = 30
    DATABASE_POOL_RECYCLE: int = 1800

    # ── 일반 ────────────────────────────────────────────
    DEBUG: bool = True


settings = Settings()
