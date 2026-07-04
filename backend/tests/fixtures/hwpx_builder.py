"""테스트용 최소 HWPX 버퍼 생성기 — 디스크 픽스처 없이 유효 파일을 즉석 구성.

HWPX 는 XML 을 zip 으로 묶은 포맷이라 순수 텍스트로 유효 파일을 만들 수 있다.
hwp-hwpx-parser.Reader 가 이 버퍼를 문단 리스트로 정확히 분리해 읽는 것을 실측 검증함
(build_hwpx(["a","b","c"]) → r.text.split("\\n") == ["a","b","c"]).
"""
import io
import zipfile

NS_HH = "http://www.hancom.co.kr/hwpml/2011/head"
NS_HC = "http://www.hancom.co.kr/hwpml/2011/core"
NS_HS = "http://www.hancom.co.kr/hwpml/2011/section"
NS_HP = "http://www.hancom.co.kr/hwpml/2011/paragraph"
NS_OCF = "urn:oasis:names:tc:opendocument:xmlns:container"
NS_HPF = "http://www.hancom.co.kr/schema/2011/hpf"


def build_hwpx(paragraphs: list[str]) -> bytes:
    container_xml = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<ocf:container xmlns:ocf="{NS_OCF}" xmlns:hpf="{NS_HPF}"><ocf:rootfiles>'
        '<ocf:rootfile full-path="Contents/content.hpf" media-type="application/hwpml-package+xml"/></ocf:rootfiles></ocf:container>')

    content_hpf = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<hpf:package xmlns:hpf="{NS_HPF}" xmlns:opf="http://www.idpf.org/2007/opf/" '
        'xmlns:dc="http://purl.org/dc/elements/1.1/" version="1.4">'
        '<hpf:head><opf:metadata><opf:title>t</opf:title></opf:metadata></hpf:head>'
        '<opf:manifest>'
        '<opf:item id="header" href="Contents/header.xml" media-type="application/xml"/>'
        '<opf:item id="section0" href="Contents/section0.xml" media-type="application/xml"/>'
        '</opf:manifest>'
        '<opf:spine><opf:itemref idref="section0" linetype="user"/></opf:spine></hpf:package>')

    header_xml = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<hh:head xmlns:hh="{NS_HH}" xmlns:hc="{NS_HC}" version="1.4" secCnt="1"><hh:refList>'
        '</hh:refList></hh:head>')

    def para(text, pid):
        return (f'<hp:p id="{pid}" paraPrIDRef="0" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0">'
                f'<hp:run charPrIDRef="0"><hp:t>{text}</hp:t></hp:run></hp:p>')

    section_xml = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<hs:sec xmlns:hs="{NS_HS}" xmlns:hp="{NS_HP}" xmlns:hc="{NS_HC}">'
        + ''.join(para(t, i) for i, t in enumerate(paragraphs)) + '</hs:sec>')

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(zipfile.ZipInfo("mimetype"), "application/hwp+zip", compress_type=zipfile.ZIP_STORED)
        z.writestr("META-INF/container.xml", container_xml)
        z.writestr("Contents/content.hpf", content_hpf)
        z.writestr("Contents/header.xml", header_xml)
        z.writestr("Contents/section0.xml", section_xml)
    return buf.getvalue()
