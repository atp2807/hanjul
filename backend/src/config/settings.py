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

    # ── 정산/출금 ───────────────────────────────────────
    # 작가 출금계좌번호 암호화 키(Fernet, base64 32B). 비면 dev 임시키 파생(운영 필수 주입).
    SETTLEMENT_ENC_KEY: str = ""

    # ── 운영자(potato) 별도 인증 영역 ───────────────────
    # 고객 JWT와 분리된 시크릿 — 키 자체가 방화벽(고객 토큰은 potato 서명검증 실패).
    POTATO_JWT_SECRET_KEY: str = "dev-insecure-potato-change-me"
    POTATO_JWT_TTL_HOURS: int = 12
    # 운영자 콘솔 IP 화이트리스트 — CSV. 비면 무제한(dev). 운영은 허용 IP만.
    # api.hanjul.io는 Cloudflare 프록시 → 진짜 클라 IP는 CF-Connecting-IP 헤더.
    POTATO_ALLOWED_IPS: str = ""

    # ── 소셜 OAuth ──────────────────────────────────────
    # 활성 provider (나라별 확장: GOOGLE,NAVER,KAKAO,LINE…). CSV.
    AUTH_PROVIDERS: str = "GOOGLE"
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:28000/api/auth/google/callback"
    # 소셜 콜백 후 토큰을 들고 돌아갈 프론트 주소 (프로덕션은 https://www.hanjul.io)
    FRONTEND_URL: str = "http://localhost:35173"
    # CORS 허용 출처 — 콤마구분. 운영은 https://www.hanjul.io 등 추가. FRONTEND_URL은 자동 포함.
    CORS_ORIGINS: str = "http://localhost:35173,http://localhost:35200"

    @property
    def cors_origin_list(self) -> list[str]:
        origins = [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]
        if self.FRONTEND_URL and self.FRONTEND_URL not in origins:
            origins.append(self.FRONTEND_URL)
        return origins

    # ── 결제(PG) ────────────────────────────────────────
    PORTONE_API_SECRET: str = ""
    # 데모 모드: 결제 검증을 건너뛰고 성공 처리 (개발/데모 전용). 운영은 반드시 False.
    PAYMENT_DEMO: bool = False
    # Toss Payments — PAYMENT_DEMO=False면 실연동. 테스트키는 샌드박스(test_ck_/test_sk_).
    TOSS_TEST_CLIENT_KEY: str = ""   # 공개키(프론트 위젯) — clientKey
    TOSS_TEST_SECRET_KEY: str = ""   # 시크릿(백엔드 confirm Basic auth)
    TOSS_TEST_SECURITY_KEY: str = ""  # 빌링/지급대행 보안키(현재 미사용, 백업)
    # Mock 모드: 외부 호출 없이 confirm 성공 응답 (단위테스트/오프라인). 운영은 False.
    TOSS_PAYMENT_MOCK_MODE: bool = False

    # ── AI 표지(novelpotato) ────────────────────────────
    # 데모: 외부 호출 없이 placeholder 반환 (dev/E2E). 운영은 False + 아래 설정.
    COVER_DEMO: bool = False
    COVER_API_URL: str = ""  # novelpotato /generate-cover
    COVER_API_KEY: str = ""
    # 표지 직접 업로드 — 로컬 디스크 저장 + /uploads 정적 서빙. PUBLIC_API_URL 로 절대 URL 구성.
    UPLOAD_DIR: str = "uploads"
    PUBLIC_API_URL: str = "http://localhost:28000"

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

    @property
    def potato_allowed_ip_list(self) -> list[str]:
        return [ip.strip() for ip in self.POTATO_ALLOWED_IPS.split(",") if ip.strip()]


settings = Settings()
