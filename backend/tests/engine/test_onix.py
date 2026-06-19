"""ONIX 3.0 메타데이터 생성 테스트."""
from src.engine.publishing.onix import OnixProduct, build_onix


def test_onix_with_isbn():
    xml = build_onix(
        OnixProduct(
            record_reference="bk1", title="한 줄", language="ko",
            isbn="9788912345678", author="박작가", price_amt=12000,
        ),
        "20260619",
    )
    assert 'release="3.0"' in xml
    assert "<ProductIDType>15</ProductIDType>" in xml  # ISBN-13
    assert "9788912345678" in xml
    assert "<TitleText>한 줄</TitleText>" in xml
    assert "박작가" in xml
    assert "<LanguageCode>kor</LanguageCode>" in xml
    assert "<ProductForm>EB</ProductForm>" in xml and "E101" in xml  # EPUB
    assert "<PriceAmount>12000</PriceAmount>" in xml
    assert "<PublisherName>한줄</PublisherName>" in xml


def test_onix_without_isbn_uses_proprietary():
    xml = build_onix(OnixProduct(record_reference="bk1", title="x", language="en"), "20260619")
    assert "<ProductIDType>01</ProductIDType>" in xml
    assert "HANJUL" in xml
    assert "<LanguageCode>eng</LanguageCode>" in xml


def test_onix_free_book_no_price():
    xml = build_onix(OnixProduct(record_reference="b", title="무료", language="ko"), "20260619")
    assert "<Price>" not in xml


def test_onix_no_author_omits_contributor():
    xml = build_onix(OnixProduct(record_reference="b", title="x", language="ko"), "20260619")
    assert "<Contributor>" not in xml
