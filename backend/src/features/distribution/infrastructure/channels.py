"""서점 배포 채널 어댑터 + 레지스트리.

- DemoDistributionChannel: 전송 없이 성공 처리 (개발/데모, DISTRIBUTION_DEMO).
- SftpDistributionChannel: 서점 SFTP에 EPUB+ONIX 업로드 (실연동 — host/계정은 설정에서).
"""
from src.config.settings import Settings
from src.features.distribution.domain.models import DistributionChannel, UnknownChannel


class DemoDistributionChannel:
    def __init__(self, channel: str = "DEMO"):
        self.channel = channel

    async def deliver(self, reference: str, epub: bytes, onix: str, filename: str) -> None:
        return  # 데모: 성공 가정


class SftpDistributionChannel:
    """서점 SFTP 채널 — EPUB + ONIX 업로드. 실연동은 host/계정 필요(설정)."""

    def __init__(self, channel: str, host: str, port: int, username: str, password: str, remote_dir: str):
        self.channel = channel
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._dir = remote_dir.rstrip("/")

    async def deliver(self, reference: str, epub: bytes, onix: str, filename: str) -> None:
        import asyncssh  # lazy — 실연동 시에만 필요

        async with asyncssh.connect(
            self._host, port=self._port, username=self._username,
            password=self._password, known_hosts=None,
        ) as conn:
            async with conn.start_sftp_client() as sftp:
                async with sftp.open(f"{self._dir}/{filename}.epub", "wb") as f:
                    await f.write(epub)
                async with sftp.open(f"{self._dir}/{filename}.onix.xml", "wb") as f:
                    await f.write(onix.encode("utf-8"))


def build_channel(channel: str, settings: Settings) -> DistributionChannel:
    if settings.DISTRIBUTION_DEMO:
        return DemoDistributionChannel(channel)  # 데모는 어떤 서점이든 성공 기록
    if settings.DIST_SFTP_HOST:
        return SftpDistributionChannel(
            channel,
            host=settings.DIST_SFTP_HOST,
            port=settings.DIST_SFTP_PORT,
            username=settings.DIST_SFTP_USER,
            password=settings.DIST_SFTP_PASSWORD,
            remote_dir=settings.DIST_SFTP_DIR,
        )
    raise UnknownChannel(channel)
