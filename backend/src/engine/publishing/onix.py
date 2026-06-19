"""ONIX 3.0 메타데이터 생성 (순수). 서점/유통사가 먹는 책정보 표준 피드.

ebook(EPUB) 단권 기준 최소 유효 레코드. 시각은 외부 주입 → 결정론.
"""
import html as _html
from dataclasses import dataclass

PUBLISHER = "한줄"

# ISO 639-2/B 3자리 (ONIX LanguageCode)
_LANG = {"ko": "kor", "en": "eng", "ja": "jpn", "zh": "chi"}


@dataclass
class OnixProduct:
    record_reference: str   # 고유 참조 (책 id)
    title: str
    language: str           # ko | en | ...
    isbn: str | None = None
    author: str | None = None
    price_amt: int | None = None
    currency: str = "KRW"


def _esc(s: str | None) -> str:
    return _html.escape(s or "", quote=True)


def _product_identifier(p: OnixProduct) -> str:
    if p.isbn:
        # 15 = ISBN-13
        return (
            "    <ProductIdentifier>\n"
            "      <ProductIDType>15</ProductIDType>\n"
            f"      <IDValue>{_esc(p.isbn)}</IDValue>\n"
            "    </ProductIdentifier>\n"
        )
    # 01 = proprietary (ISBN 미부여 시)
    return (
        "    <ProductIdentifier>\n"
        "      <ProductIDType>01</ProductIDType>\n"
        "      <IDTypeName>HANJUL</IDTypeName>\n"
        f"      <IDValue>{_esc(p.record_reference)}</IDValue>\n"
        "    </ProductIdentifier>\n"
    )


def _contributor(p: OnixProduct) -> str:
    if not p.author:
        return ""
    return (
        "      <Contributor>\n"
        "        <ContributorRole>A01</ContributorRole>\n"   # 저자
        f"        <PersonName>{_esc(p.author)}</PersonName>\n"
        "      </Contributor>\n"
    )


def _price(p: OnixProduct) -> str:
    if p.price_amt is None:
        return ""
    return (
        "    <ProductSupply>\n      <SupplyDetail>\n"
        "        <Price>\n"
        "          <PriceType>02</PriceType>\n"            # 소비자가(부가세 포함)
        f"          <PriceAmount>{p.price_amt}</PriceAmount>\n"
        f"          <CurrencyCode>{_esc(p.currency)}</CurrencyCode>\n"
        "        </Price>\n"
        "      </SupplyDetail>\n    </ProductSupply>\n"
    )


def build_onix(p: OnixProduct, sent_date: str) -> str:
    """OnixProduct → ONIX 3.0 XML. sent_date = YYYYMMDD."""
    lang = _LANG.get(p.language, "und")
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<ONIXMessage release="3.0" xmlns="http://ns.editeur.org/onix/3.0/reference">\n'
        "  <Header>\n"
        f"    <Sender><SenderName>{PUBLISHER}</SenderName></Sender>\n"
        f"    <SentDateTime>{_esc(sent_date)}</SentDateTime>\n"
        "  </Header>\n"
        "  <Product>\n"
        f"    <RecordReference>{_esc(p.record_reference)}</RecordReference>\n"
        "    <NotificationType>03</NotificationType>\n"   # 확정
        + _product_identifier(p) +
        "    <DescriptiveDetail>\n"
        "      <ProductComposition>00</ProductComposition>\n"
        "      <ProductForm>EB</ProductForm>\n"            # 디지털
        "      <ProductFormDetail>E101</ProductFormDetail>\n"  # EPUB
        "      <TitleDetail>\n        <TitleType>01</TitleType>\n"
        "        <TitleElement>\n          <TitleElementLevel>01</TitleElementLevel>\n"
        f"          <TitleText>{_esc(p.title)}</TitleText>\n"
        "        </TitleElement>\n      </TitleDetail>\n"
        + _contributor(p) +
        f"      <Language><LanguageRole>01</LanguageRole><LanguageCode>{lang}</LanguageCode></Language>\n"
        "    </DescriptiveDetail>\n"
        "    <PublishingDetail>\n"
        f"      <Publisher><PublishingRole>01</PublishingRole><PublisherName>{PUBLISHER}</PublisherName></Publisher>\n"
        "      <PublishingStatus>04</PublishingStatus>\n"  # 출판중(active)
        "    </PublishingDetail>\n"
        + _price(p) +
        "  </Product>\n"
        "</ONIXMessage>"
    )
