"""sitemap.xml 생성 (순수). sitemaps.org 0.9 스키마.

ONIX(onix.py)와 동일한 패턴 — 데이터를 인자로 받아 문자열을 조립할 뿐, DB·설정에
접근하지 않는다. 시각 포맷은 호출자가 결정론적으로 넘긴다.
"""
import html as _html
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

_XMLNS = "http://www.sitemaps.org/schemas/sitemap/0.9"


def _esc(s: str) -> str:
    return _html.escape(s, quote=True)


def _fmt_date(dt: datetime | None) -> str | None:
    """lastmod = YYYY-MM-DD (W3C Datetime, sitemaps.org 권장 최소 정밀도)."""
    return dt.date().isoformat() if dt else None


def _url_entry(loc: str, lastmod: str | None = None) -> str:
    if lastmod:
        return f"  <url>\n    <loc>{_esc(loc)}</loc>\n    <lastmod>{lastmod}</lastmod>\n  </url>\n"
    return f"  <url>\n    <loc>{_esc(loc)}</loc>\n  </url>\n"


@dataclass
class SitemapBook:
    id: UUID
    published_at: datetime | None = None


def build_sitemap(base_url: str, static_paths: list[str], books: list[SitemapBook]) -> str:
    """base_url(스킴+호스트, trailing slash 없음) + 정적 경로들 + 공개 책 상세 URL → XML 문자열.

    static_paths: "/", "/reviewers" 처럼 선행 슬래시 포함 경로.
    """
    base = base_url.rstrip("/")
    body = "".join(_url_entry(f"{base}{path}") for path in static_paths)
    body += "".join(
        _url_entry(f"{base}/books/{b.id}", _fmt_date(b.published_at)) for b in books
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<urlset xmlns="{_XMLNS}">\n'
        f"{body}"
        "</urlset>"
    )
