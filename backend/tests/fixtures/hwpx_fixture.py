"""테스트용 최소 HWPX(한컴 문서) 바이너리 생성기.

HWPX 는 OWPML(XML)을 ZIP 으로 묶은 포맷이라 순수 텍스트로 유효 파일을 손수 만들 수
있다 — 실 HWP5 바이너리 픽스처 없이도 rhwp 의 실제 파싱 경로를 태울 수 있게 한다.
`bold=True`/`italic=True` 로 charPr 를 붙여 서식(→ marks) 전파까지 검증 가능.

주의: 여기서 검증되는 건 HWPX 경로다. HWP5(구 OLE 바이너리) 경로는 손수 만들 수 없어
실 바이너리 픽스처가 없다(커버리지 갭 — hwp_import 보고서 참조).
"""
import io
import zipfile

_NS_HP = "http://www.hancom.co.kr/hwpml/2011/paragraph"
_NS_HH = "http://www.hancom.co.kr/hwpml/2011/head"
_NS_HS = "http://www.hancom.co.kr/hwpml/2011/section"
_NS_HC = "http://www.hancom.co.kr/hwpml/2011/core"
_NS_OCF = "urn:oasis:names:tc:opendocument:xmlns:container"
_NS_ODF = "http://www.idpf.org/2007/opf/"
_NS_HPF = "http://www.hancom.co.kr/schema/2011/hpf"

_VERSION_XML = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<hv:HCFVersion xmlns:hv="http://www.hancom.co.kr/hwpml/2011/version" '
    'tagetApplication="WORDPROCESSOR" major="5" minor="1" micro="1" buildNumber="0" '
    'os="1" xmlVersion="1.4" application="Hancom Office Hangul" appVersion="12.0"/>'
)

_CONTAINER_XML = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    f'<ocf:container xmlns:ocf="{_NS_OCF}" xmlns:hpf="{_NS_HPF}"><ocf:rootfiles>'
    '<ocf:rootfile full-path="Contents/content.hpf" '
    'media-type="application/hwpml-package+xml"/></ocf:rootfiles></ocf:container>'
)

_CONTENT_HPF = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    f'<hpf:package xmlns:hpf="{_NS_HPF}" xmlns:opf="{_NS_ODF}" '
    'xmlns:dc="http://purl.org/dc/elements/1.1/" version="1.4">'
    '<hpf:head><opf:metadata><opf:title>t</opf:title></opf:metadata></hpf:head>'
    '<opf:manifest>'
    '<opf:item id="header" href="Contents/header.xml" media-type="application/xml"/>'
    '<opf:item id="section0" href="Contents/section0.xml" media-type="application/xml"/>'
    '</opf:manifest>'
    '<opf:spine><opf:itemref idref="section0" linetype="user"/></opf:spine></hpf:package>'
)


def _char_pr(cid: int, extra: str = "") -> str:
    return (
        f'<hh:charPr id="{cid}" height="1000" textColor="#000000" shadeColor="none" '
        'useFontSpace="0" useKerning="0" symMark="NONE" borderFillIDRef="2">'
        '<hh:fontRef hangul="0" latin="0" hanja="0" japanese="0" other="0" symbol="0" user="0"/>'
        '<hh:ratio hangul="100" latin="100" hanja="100" japanese="100" other="100" symbol="100" user="100"/>'
        '<hh:spacing hangul="0" latin="0" hanja="0" japanese="0" other="0" symbol="0" user="0"/>'
        '<hh:relSz hangul="100" latin="100" hanja="100" japanese="100" other="100" symbol="100" user="100"/>'
        '<hh:offset hangul="0" latin="0" hanja="0" japanese="0" other="0" symbol="0" user="0"/>'
        f'{extra}</hh:charPr>'
    )


def _header_xml() -> str:
    # charPr: 0=보통, 1=굵게(bold), 2=기울임(italic)
    cps = _char_pr(0) + _char_pr(1, "<hh:bold/>") + _char_pr(2, "<hh:italic/>")
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<hh:head xmlns:hh="{_NS_HH}" xmlns:hc="{_NS_HC}" version="1.4" secCnt="1"><hh:refList>'
        '<hh:fontfaces itemCnt="1"><hh:fontface lang="HANGUL" fontCnt="1">'
        '<hh:font id="0" face="함초롬바탕" type="TTF"><hh:typeInfo familyType="FCAT_GOTHIC" '
        'weight="0" proportion="0" contrast="0" strokeVariation="0" armStyle="0" letterform="0" '
        'midline="0" xHeight="0"/></hh:font></hh:fontface></hh:fontfaces>'
        f'<hh:charProperties itemCnt="3">{cps}</hh:charProperties>'
        '<hh:paraProperties itemCnt="1"><hh:paraPr id="0" tabPrIDRef="0" condense="0" '
        'fontLineHeight="0" snapToGrid="1" suppressLineNumbers="0" checked="0">'
        '<hh:align horizontal="JUSTIFY" vertical="BASELINE"/>'
        '<hh:heading type="NONE" idRef="0" level="0"/>'
        '<hh:breakSetting breakLatinWord="KEEP_WORD" breakNonLatinWord="KEEP_WORD" '
        'widowOrphan="0" keepWithNext="0" keepLines="0" pageBreakBefore="0" lineWrap="BREAK"/>'
        '<hh:margin><hc:intent value="0" unit="HWPUNIT"/><hc:left value="0" unit="HWPUNIT"/>'
        '<hc:right value="0" unit="HWPUNIT"/><hc:prev value="0" unit="HWPUNIT"/>'
        '<hc:next value="0" unit="HWPUNIT"/></hh:margin>'
        '<hh:lineSpacing type="PERCENT" value="160" unit="HWPUNIT"/>'
        '<hh:border borderFillIDRef="2" offsetLeft="0" offsetRight="0" offsetTop="0" '
        'offsetBottom="0" connect="0" ignoreMargin="0"/></hh:paraPr></hh:paraProperties>'
        '</hh:refList></hh:head>'
    )


def _run(text: str, cid: int = 0) -> str:
    return f'<hp:run charPrIDRef="{cid}"><hp:t>{text}</hp:t></hp:run>'


def _para(runs: str) -> str:
    return (
        '<hp:p id="0" paraPrIDRef="0" styleIDRef="0" pageBreak="0" columnBreak="0" '
        f'merged="0">{runs}</hp:p>'
    )


def build_hwpx(paragraphs: list[str]) -> bytes:
    """문단 텍스트 리스트 → 최소 HWPX 바이너리.

    각 문단은 한 개의 보통 서식 런. 서식 런이 섞인 문단은 build_hwpx_marked 사용.
    """
    body = "".join(_para(_run(t)) for t in paragraphs)
    return _zip_hwpx(body)


def build_hwpx_marked() -> bytes:
    """보통/굵게/기울임 런이 한 문단에 섞인 HWPX — marks(strong/em) 전파 검증용."""
    runs = _run("보통", 0) + _run("굵게", 1) + _run("기울임", 2)
    return _zip_hwpx(_para(runs))


def _zip_hwpx(section_body: str) -> bytes:
    section = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<hs:sec xmlns:hs="{_NS_HS}" xmlns:hp="{_NS_HP}" xmlns:hc="{_NS_HC}">'
        f'{section_body}</hs:sec>'
    )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        # mimetype 은 반드시 첫 엔트리 + 무압축(STORED)
        z.writestr(zipfile.ZipInfo("mimetype"), "application/hwp+zip", compress_type=zipfile.ZIP_STORED)
        z.writestr("version.xml", _VERSION_XML)
        z.writestr("META-INF/container.xml", _CONTAINER_XML)
        z.writestr("Contents/content.hpf", _CONTENT_HPF)
        z.writestr("Contents/header.xml", _header_xml())
        z.writestr("Contents/section0.xml", section)
    return buf.getvalue()
