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

    # ── 인증(JWT) ───────────────────────────────────────
    JWT_SECRET_KEY: str = "dev-insecure-change-me"
    JWT_ALG: str = "HS256"
    JWT_TTL_HOURS: int = 72

    # ── 소셜 OAuth ──────────────────────────────────────
    # 활성 provider (나라별 확장: GOOGLE,NAVER,KAKAO,LINE…). CSV.
    AUTH_PROVIDERS: str = "GOOGLE"
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:28000/api/auth/google/callback"
    # 소셜 콜백 후 토큰을 들고 돌아갈 프론트 주소 (프로덕션은 https://hanjul.io)
    FRONTEND_URL: str = "http://localhost:35173"

    # ── 결제(PG) ────────────────────────────────────────
    PORTONE_API_SECRET: str = ""
    # 데모 모드: 결제 검증을 건너뛰고 성공 처리 (개발/데모 전용). 운영은 반드시 False.
    PAYMENT_DEMO: bool = False

    # ── AI 표지(novelpotato) ────────────────────────────
    COVER_API_URL: str = ""
    COVER_API_KEY: str = ""

    # ── 서점 배포 ───────────────────────────────────────
    # 데모: 실제 전송 없이 성공 기록 (개발). 운영은 False + 아래 SFTP 설정.
    DISTRIBUTION_DEMO: bool = False
    DIST_SFTP_HOST: str = ""
    DIST_SFTP_PORT: int = 22
    DIST_SFTP_USER: str = ""
    DIST_SFTP_PASSWORD: str = ""
    DIST_SFTP_DIR: str = "/upload"

    # ── 일반 ────────────────────────────────────────────
    DEBUG: bool = True
    # E2E/로컬 전용 로그인 우회(/api/auth/test-login) 허용. 운영은 반드시 False(fail-closed).
    E2E_LOGIN_ENABLED: bool = False

    @property
    def auth_provider_list(self) -> list[str]:
        return [p.strip().upper() for p in self.AUTH_PROVIDERS.split(",") if p.strip()]


settings = Settings()
