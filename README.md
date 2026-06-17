# 한줄 (hanjul.io) — 글로벌 ebook 출판 플랫폼

유페이퍼의 세련된 버전. 작가가 직접 출판·판매·정산하는 셀프퍼블리싱 플랫폼 +
GitHub식 ebook 저작툴. 아시아 / 일반서적 + 웹소설 타겟.

## 모노레포 구조

```
hanjul/
  backend/   FastAPI + SQLAlchemy 2.0 + PostgreSQL   (Python)
  web/       React 19 + Vite + 순수 JS + Pretext     (예정)
```

## 엔진 아키텍처

```
입력 (TXT/MD/DOCX/HWP/PDF)
   │  변환 (juldoc / pymupdf)
정본 HTML/XHTML  ← 단일 진실 소스
   │
   ├─▶ 웹 리더 (프론트 Pretext 조판 — 페이지네이션·재조판)
   ├─▶ EPUB export (e-ink 리더기는 기기 자체 엔진이 렌더)
   └─▶ PDF export
```

- **juldoc** = 렌더 ("무엇을 그릴지")
- **Pretext** = 조판 ("어떻게 페이지로 나눌지", 프론트엔드 텍스트 전담)

설계 기록: LinkLore `dc-d362244d`(비전) · `dc-f8acfa26`(기능리스트) ·
`lr-9fd9d241`(조판) · `lr-635fa8cc`(모델) · `lr-8abc20a6`(스택).

## 로드맵

- **P1** 유페이퍼 세련화 (단권 셀프퍼블리싱) ← 현재
- **P2** 회차 연재
- **P3** 전자책 앱 (e-ink는 EPUB)
