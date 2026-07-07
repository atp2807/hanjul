# AI 글쓰기 도구 시장조사 — Sudowrite / Novelcrafter / 뮤블(Muvel) / Scrivener

- 조사일: 2026-07-06
- 목적: '한줄' 웹소설 플랫폼이 저작(글쓰기 IDE)-출판-판매를 하나로 묶은 도구를 만들 가치가 있는지 판단하기 위한 근거 자료 수집. 특히 "AI가 장편 전체 컨텍스트를 못 다룬다"는 문제를 각 도구가 어떻게 풀고 있는지(Story Bible, 코덱스 등 구조화 방식)와 그 채택 반응을 중점 조사.
- 방법: deep-research 워크플로 (5개 검색 각도 → 18개 소스 fetch → 78개 클레임 추출 → 상위 25개 클레임에 대해 3표 적대적 검증, 2/3 반박 시 폐기) → synthesis.
- 통계: 소스 18개 fetch, 클레임 78개 추출, 25개 검증, 16개 확인(confirmed) / 9개 반박(killed) / 0개 미검증, synthesis 후 9개 finding으로 병합.

## Executive Summary

모든 3개 AI 글쓰기 도구(Sudowrite, Novelcrafter, Muvel)는 "AI가 장편 전체 컨텍스트를 못 다룬다"는 문제를 구조화된 스토리바이블/코덱스 시스템으로 풀고 있으며 — Sudowrite의 계단식 Story Bible 파이프라인, Novelcrafter의 Codex+Story Beats, 뮤블의 위키+다이나믹링크 — 이는 이제 업계 표준 기능이지 차별화 포인트가 아니다.

뮤블의 실제 흥행 요인은 AI 혁신보다는 (1) 설치형 완전 무료 + 후원 기반 모델(Scrivener의 OS당 약 8만원 라이선스와 대비), (2) 웹소설 특화 워크플로(에피소드/위키/메모 3분류, 범용 '문서' 형식 부재), (3) 1인 비개발자가 만들었음에도 사용자 불만(맞춤법 검사기 부재 등)에 수주 내로 대응하는 빠른 반복 개발이었다.

반대로 조사된 4개 도구 중 어느 것도 저작(글쓰기)-출간-판매 파이프라인을 하나로 통합한 사례는 확인되지 않았다 — 이는 '한줄'이 파고들 수 있는 명확한 공백이며, 동시에 시장에 선례가 없어 검증되지 않은 가설이라는 뜻이기도 하다.

다만 이번 조사에서는 각 도구의 실제 사용자 수/시장점유율 같은 정량 지표는 전혀 확인되지 않았고, 뮤블 관련 근거 다수가 나무위키·커뮤니티 등 2차 출처에 의존한다는 한계가 있다.

## 확인된 Findings (adversarial 3표 검증 통과)

### 1. 뮤블의 포지셔닝 — "소설 집필 전용 에디터"
뮤블은 스크리브너/노벨라/한글/한컴독스/구글독스/옵시디언 등 범용 및 경쟁 도구와의 공개 비교표를 통해 '소설 집필 전용 에디터'로 스스로를 포지셔닝한다 (가격정책, 플랫폼, 클라우드 동기화, 스타일링, 에디터 기능, 소설관리 기능, 안전장치, 내보내기 형식 등 항목 비교).
- 신뢰도: high · 투표: 3-0
- 출처: https://guide.muvel.app/getting-started/editor-comparison

### 2. 뮤블의 비즈니스 모델 — 후원 기반 완전 무료
뮤블의 비즈니스 모델은 유료 구독이 아닌 자발적 후원(패트리온) 기반이며, 설치형 버전은 서비스 상태와 무관하게 영구 무료 사용이 보장된다. 2026년 5월 기준 완전 무료로 운영 중이며, 이는 스크리브너의 OS별 약 8만원(59.99달러) 영구 라이선스 비용과 대비된다.
- 신뢰도: high · 투표: 3-0 (관련 3개 클레임 병합)
- 출처: https://muvel.app/en , https://muvel.app/info , https://patreon.com/posts/myubeul-muvel-133564363 , https://pensiv.so/ko/blog/muvel-alternative

### 3. 뮤블의 출시 속도와 반복 개발
뮤블은 2025년 4월 17일 아이디어 게시 후 단 5일 만인 4월 22일 베타 출시되었고, 비개발자(작가)로 알려진 1인 개발자가 만들었으며 이후에도 거의 매일 단위로 업데이트가 이뤄질 만큼 극도로 빠른 반복 개발을 지속했다.
- 신뢰도: medium · 투표: 2-1 (유일하게 완전 만장일치 아님)
- 출처: https://namu.wiki/w/뮤블 (2차, 직접 fetch 403 차단) , https://gall.dcinside.com/mgallery/board/view/?id=tgijjdd&no=1087977 (개발자 본인 게시물로 교차검증)

### 4. 뮤블의 장편 컨텍스트 구조화 방식
뮤블은 장편 컨텍스트 관리를 위해 프로젝트를 원고(에피소드)/설정집(위키)/메모의 3가지 고정 문서 유형으로만 구조화하고 범용 '문서' 형식을 두지 않는다. 위키는 본문에 명칭이 언급되면 자동 링크가 걸리는 '다이나믹 링크'를 지원하며, AI 맞춤법 검사(AI 더블체크)도 이 위키 내용을 참조해 등장인물명 등 고유명사에 대한 과잉교정을 회피한다. AI가 작성된 에피소드를 리뷰/줄거리 요약해주는 기능도 있으며, 콘텐츠는 AI 학습에 사용되지 않는다는 프라이버시 메시지를 명시한다.
- 신뢰도: high · 투표: 3-0 (관련 3개 클레임 병합)
- 출처: https://namu.wiki/w/뮤블 , https://guide.muvel.app/novel , https://muvel.app/en

### 5. 뮤블의 맞춤법 검사기 도입 경위 — 빠른 반복의 실증 사례
뮤블은 출시 당시 내장 맞춤법 검사기를 지원하지 않아 맞춤법 검사가 필수인 사용자들이 경쟁 서비스 '노벨라'를 선호하는 이탈 요인이 있었으나, 약 5주 뒤인 2025년 5월 28일 v2.4.5 업데이트에서 (카카오가 공식 API를 제공하지 않아 비공식 방식의) 다음 맞춤법 검사기 연동을 추가해 이 약점을 해소했다.
- 신뢰도: high · 투표: 3-0
- 출처: https://namu.wiki/w/뮤블 , https://gall.dcinside.com/mgallery/board/view/?id=tgijjdd&no=1094685 (개발자 본인 공지)

### 6. Sudowrite 최상위 티어 — 다작/전업 작가 타겟
Sudowrite의 최상위 소비자 티어 'Max'는 월 44달러/200만 크레딧이며 '연간 여러 번 출간하는 작가'를 명시적 타겟으로 하고 미사용 크레딧은 12개월 이월된다 — 캐주얼 사용자가 아닌 다작/전업 작가층을 겨냥한 가격 설계임을 시사.
- 신뢰도: high · 투표: 3-0
- 출처: https://sudowrite.com/pricing

### 7. Sudowrite의 Story Bible — 계단식 파이프라인
Sudowrite의 Story Bible은 Braindump→Genre/Style→Synopsis→Characters/Worldbuilding→Outline→Scenes로 이어지는 계단식(cascading) 파이프라인으로, 앞 단계의 산출물이 다음 단계 생성을 제약/보조한다. (1) 작가의 집필 과정을 단계별로 조직화하고 (2) AI 산출물이 이미 확정된 설정과 일관되도록 유지하는 이중 목적을 갖는다 — 조사된 3개 도구 중 가장 명시적이고 정교한 '장편 컨텍스트' 구조화 방식.
- 신뢰도: high · 투표: 3-0 (관련 2개 클레임 병합)
- 출처: https://docs.sudowrite.com/using-sudowrite/1ow1qkGqof9rtcyGnrWUBS/what-is-story-bible/jmWepHcQdJetNrE991fjJC

### 8. Novelcrafter의 BYOK 가격 모델
Novelcrafter는 소프트웨어 구독료와 AI 사용 비용을 완전히 분리하는 'BYOK(Bring Your Own Key)' 모델을 채택한다 — $4(Scribe)~$20(Specialist)의 모든 유료 티어에서 AI 비용은 별도로 OpenRouter/OpenAI 등에 직접 지불하며, 구독료에 AI 크레딧이 포함되지 않는다. 이는 Sudowrite의 크레딧 번들형 모델과 대비된다.
- 신뢰도: high · 투표: 3-0 (관련 2개 클레임 병합)
- 출처: https://www.novelcrafter.com/pricing , https://www.novelcrafter.com/help/faq/ai-and-prompting/ai-cost

### 9. Novelcrafter의 Codex — 구조화된 코덱스가 핵심 해법
Novelcrafter의 Codex는 캐릭터/장소/설정을 커스터마이즈 가능한 필드로 관리하는 구조화 데이터베이스이며, AI 연동이 전혀 없는 최저가 $4/월(Scribe) 티어에도 기본 제공된다. Story Beats(장면 단위 개요)와 결합되어 AI 생성 시 코덱스 데이터를 직접 참조시키는 방식으로, 'AI의 원시 컨텍스트 창'에 의존하지 않고 구조화·선별된 컨텍스트를 공급하는 것이 이 도구의 핵심 해법이다.
- 신뢰도: high · 투표: 3-0 (관련 3개 클레임 병합)
- 출처: https://www.novelcrafter.com/help/docs/codex/the-codex , https://docs.novelcrafter.com/en/articles/8675743-the-codex , https://www.novelcrafter.com/pricing , https://sudowrite.com/blog/sudowrite-vs-novelcrafter-the-ultimate-ai-showdown-for-novelists/

## 반박되어 폐기된 클레임 (투명성 목적으로 기록)

| 클레임 | 투표(생존-반박) | 출처 |
|---|---|---|
| 뮤블은 웹소설 특화 구조화 도구(회차 자동관리, 캔버스/마인드맵)로 경쟁사 대비 차별화한다 | 0-3 | guide.muvel.app/getting-started/editor-comparison |
| 뮤블은 위키+플롯 캔버스로 "AI가 장편 컨텍스트를 못 다룬다"는 문제에 대응한다(스토리바이블/코덱스 상당) | 0-3 | muvel.app/en |
| Sudowrite Hobby & Student 티어는 $10/월·225,000 크레딧, 캐주얼/학생 타겟 | 0-3 | sudowrite.com/pricing |
| Professional 티어($22/월, 450,000 크레딧)가 장편소설 작업을 명시적으로 겨냥하며 피드백 기능이 추가되는 유일한 티어 | 0-3 | sudowrite.com/pricing |
| Sudowrite는 Story Bible을 인간 작가와 AI가 함께 참조하는 단일 레퍼런스로 프레이밍한다 | 1-2 | docs.sudowrite.com (Story Bible) |
| 모델 티어별 실제 AI 사용 비용은 예시 프롬프트당 $0.01~$0.31로 편차가 크다 | 1-2 | novelcrafter.com/help/faq/ai-and-prompting/ai-cost |
| 뮤블은 AI 집필 보조 기능을 지원하지 않는다 | 0-3 | pensiv.so/ko/blog/muvel-alternative |
| 뮤블에는 설정 충돌 방지/캐릭터 관계 시각화 구조화 시스템이 없다 | 0-3 | pensiv.so/ko/blog/muvel-alternative |
| Sudowrite는 크레딧 기반, Novelcrafter는 무제한 정액(all-you-can-eat) 구독 모델이다 | 0-3 | sudowrite.com/blog (경쟁사 비교 블로그) |

## 한계 (Caveats)

- 뮤블 관련 다수 핵심 근거(출시 타임라인, 후원 모델, 맞춤법 검사기 도입 경위, 문서 구조)가 나무위키(2차 출처, 직접 fetch는 403으로 차단되어 개발자 본인의 DCInside 게시물·공식 사이트·독립 커뮤니티 검색 결과로 교차 검증함)와 아카라이브/디시인사이드 커뮤니티 게시물에 의존하고 있어, 원문 그대로의 재확인은 제한적이었다.
- 뮤블 origin story 클레임은 유일하게 2-1로 완전 만장일치가 아니었다.
- 이번 조사는 정성적(포지셔닝·가격·기능구조) 근거에 집중되어 있으며, 4개 도구 각각의 실제 MAU/매출/시장점유율 등 **정량 데이터는 어떤 클레임에서도 확인되지 않았다** — '한줄'이 목표로 하는 저작-출판-판매 통합의 시장 기회 크기를 정량적으로 뒷받침할 근거는 이번 조사 범위 밖이다.
- 뮤블은 2025년 4월 출시된 신생 서비스로 가격정책·기능이 빠르게 변할 수 있어 시간민감성이 높다(조사 시점 2026-07-06 기준).
- Scrivener 관련해서는 가격(OS당 $59.99)만 확인되었고 'Word 대비 성공한 이유'에 대한 직접적 사용자 행태 근거(왜 갈아탔는가)는 3표 검증을 통과한 클레임 목록에 포함되지 않았다 — 조사 공백으로 남음.

## 남은 질문 (Open Questions)

1. 뮤블의 실제 사용자 수(MAU/가입자 수)와 한국 웹소설 작가 시장 내 침투율은 얼마나 되는가 — 이번 조사에서 정량 지표가 전혀 확인되지 않음.
2. Sudowrite/Novelcrafter/뮤블/Scrivener 중 실제로 저작-출간-판매(플랫폼 업로드/유통)를 하나의 파이프라인으로 연결한 사례가 있는가, 아니면 4개 도구 모두 '저작' 단계에만 머물러 있는가.
3. Scrivener가 Word 대비 성공한 구체적 사용자 전환 요인(폴더/코르크보드/아웃라이너 등)에 대한 1차 근거가 이번 검증에서 확보되지 못했다 — 별도 조사 필요.
4. 협업(공동집필) 기능 부재가 실제로 어느 정도의 사용자 이탈/불만을 야기하는지에 대한 정량적 근거가 부족하다 — 각 도구의 협업 기능 지원 여부와 사용자 반응을 추가로 조사할 필요.

## 전체 소스 목록

| URL | 품질 | 각도 | 추출 클레임 수 |
|---|---|---|---|
| https://namu.wiki/w/뮤블 | secondary | 한국 웹소설 시장 · 뮤블 실사용 후기 | 5 |
| https://arca.live/b/webfiction/144423850 | forum | 한국 웹소설 시장 · 뮤블 실사용 후기 | 5 |
| https://arca.live/b/webfiction/135298445 | unreliable | 한국 웹소설 시장 · 뮤블 실사용 후기 | 0 |
| https://guide.muvel.app/getting-started/editor-comparison | primary | 한국 웹소설 시장 · 뮤블 실사용 후기 | 5 |
| https://pensiv.so/ko/blog/muvel-alternative | blog | 한국 웹소설 시장 · 뮤블 실사용 후기 | 4 |
| https://muvel.app/en | primary | 한국 웹소설 시장 · 뮤블 실사용 후기 | 5 |
| https://sudowrite.com/pricing | primary | Sudowrite/Novelcrafter 가격·비즈니스 모델·Story Bible | 4 |
| https://docs.sudowrite.com/.../what-is-story-bible | primary | Sudowrite/Novelcrafter 가격·비즈니스 모델·Story Bible | 4 |
| https://www.novelcrafter.com/pricing | primary | Sudowrite/Novelcrafter 가격·비즈니스 모델·Story Bible | 5 |
| https://www.novelcrafter.com/help/docs/codex/the-codex | primary | Sudowrite/Novelcrafter 가격·비즈니스 모델·Story Bible | 3 |
| https://sudowrite.com/blog/sudowrite-vs-novelcrafter-the-ultimate-ai-showdown-for-novelists/ | blog | Sudowrite/Novelcrafter 가격·비즈니스 모델·Story Bible | 5 |
| https://www.novelcrafter.com/help/faq/ai-and-prompting/ai-cost | primary | Sudowrite/Novelcrafter 가격·비즈니스 모델·Story Bible | 3 |
| https://selfpublishingadvice.org/writing-why-i-moved-from-word-to-scrivener/ | blog | Scrivener vs Word 성공 요인 회고 | 5 |
| https://goinswriter.com/scrivener/ | blog | Scrivener vs Word 성공 요인 회고 | 5 |
| https://www.novel-software.com/scrivener-vs-word/ | blog | Scrivener vs Word 성공 요인 회고 | 5 |
| https://medium.com/a-writers-life/why-you-should-use-scrivener-for-your-novel-160f3ae36022 | blog | Scrivener vs Word 성공 요인 회고 | 5 |
| https://ilampadmanabhan.medium.com/novelcrafter-review-powerful-for-fiction-writers-frustrating-to-set-up-april-2026-64d391c629a2 | blog | AI 글쓰기 도구 사용자 불만·이탈 사유 | 5 |
| https://www.novelcrafter.com/features/codex | blog | 장편소설 AI 컨텍스트 한계와 업계 최신 동향 | 5 |

## 추가 조사 (2026-07-06, 대화 세션 중 발견 — 정본에 소급 반영)

최초 deep-research 워크플로(위 섹션)는 Sudowrite/Novelcrafter/뮤블/Scrivener 4개만 다뤘음. 이후 대화 중 수동 리서치(WebSearch/WebFetch/GitHub API)로 추가 확인한 내용을 아래에 소급 반영함 — 이 섹션은 워크플로의 3표 적대적 검증을 거치지 않은 단일 소스 확인이므로 신뢰도는 위 findings보다 낮게 취급할 것.

### 뮤블의 실제 라이벌 3곳 — 장단점 비교

| 도구 | 포지셔닝 | 장점 | 단점/약점 | 가격 |
|---|---|---|---|---|
| **노벨라 (Novella)** | 원조 웹소설 특화 에디터, 뮤블 이전 시장 1위 | 플롯/캐릭터 기능(블록 에디팅), 서버 저장으로 기기간 동기화, 문서를 플롯에 참조 연결 가능 | 유료화 이후 10만자 제한 — 이 조치가 커뮤니티의 대규모 뮤블 이탈을 촉발함 | 유료화(과거 무료 → 현재 글자수 제한형 유료) |
| **뮤블 (Muvel)** | 일반 사용자 중심 무료 대안 | 완전 무료(후원제), 데스크톱+모바일 로컬/오프라인 저장, 빠른 반복 개발, 다음 맞춤법 검사기(2025-05 추가로 노벨라 장점 흡수) | AI 집필 보조 없음, 설정 충돌 자동 감지 없음(수동 확인), epub/pdf 자체 제작 기능 없음(txt/hwp·docx/html/json만) | 설치형 무료, 클라우드는 후원제 |
| **펜시브 (Pensiv)** | "네이버 연재 작가들이 검증"한 프로 작가용 상위 도전자 | AI 집필 보조(Ask/Plan/Agent/Review), 그래프 뷰로 설정 충돌 자동 방지, 독스/플롯보드/캐릭터/캔버스로 세분화된 구조, HWP·EPUB 외부 포맷 내보내기 지원 | 뮤블 대비 신생·인지도 낮음(출처 자체가 펜시브 자체 블로그라 자사 비교라는 점 감안 필요) | 기본 무료 + 고급 기능 유료 |

경쟁 구도 패턴: 노벨라(유료화 실책) → 뮤블(무료로 치고 올라옴) → 펜시브(AI+프로타겟으로 뮤블 위를 노림). "무료가 유료를 이긴다"에서 "AI+검증된 전문성이 무료를 위협한다" 국면으로 넘어가는 중.

출처: https://guide.muvel.app/getting-started/editor-comparison , https://pensiv.so/ko/blog/muvel-alternative , https://namu.wiki/w/%EB%85%B8%EB%B2%A8%EB%9D%BC , https://gall.dcinside.com/mgallery/board/view/?id=tgijjdd&no=1088201 , https://gall.dcinside.com/mgallery/board/view/?id=tgijjdd&no=1136146

### 뮤블 실사용 규모 (정량 데이터 — 최초 조사의 공백을 메움)

| 지표 | 값 |
|---|---|
| 공식 디스코드 멤버 | 1,838명 (225명 온라인, 2026-07-06 기준) |
| GitHub 릴리즈 누적 다운로드 | 504,907회 (113개 릴리즈, 2025-05 출시 ~ 현재) |
| 최대 단일 릴리즈 다운로드 | v2.7.10 145,292회 / v2.8.7 115,579회 |

주의: 데스크톱 앱은 Tauri 자동업데이트가 GitHub Release를 백엔드로 쓰므로 이 수치는 신규 유저 수가 아니라 기존 설치 유저의 자동업데이트 체크까지 포함된 누적치. Google Play 정확한 설치수/평점은 페이지가 JS 렌더링이라 확인 불가.

출처: https://discord.com/api/invites/jAbqy6JXsk , https://github.com/KimuSoft/muvel-public/releases (GitHub API)

### 뮤블 파일 형식 — "문서"는 지원, "책 꼴"은 미지원

자체 프로젝트 파일: `.muvl`(로컬 프로젝트), `.mvle`(에피소드), `.mvlm`(메모).
내보내기 지원: txt / hwp·hwpx(서식 손실) / doc·docx(서식 손실) / html / json.
**미지원: epub, pdf.** GitHub 이슈 #38(closed)에서 개발자 본인이 "이 기능은 뮤블 자체의 epub 내보내기와 별개임"이라고 명시 — epub 자체 제작 기능은 아예 없고, 서식을 평문 규칙으로 변환해 유저가 직접 외부에서 epub을 만들도록 돕는 우회 기능만 있음. PDF는 조판(페이지네이션/한글 줄바꿈 규칙/목차)이 필요해 기술적으로 더 어려운 반면, epub은 zip+XHTML 패키징이라 상대적으로 쉬운 편 — 1인/소규모 개발 리소스가 우선순위에서 밀린 것으로 추정.

출처: https://guide.muvel.app/getting-started/editor-comparison , https://github.com/KimuSoft/muvel-public/issues/38

### 뮤블 "운영 감각"의 실체 — 겉보기와 다름

- **GitHub 이슈 트래커는 유저 피드백 채널이 아니라 개발자 자신의 백로그였음.** 최근 이슈 100개 중 97개가 "Kimu-Nowchira"(개발자/팀 계정) 본인 작성, 외부 유저는 3명뿐(firecomputer, Kifiopqk1, arilofi). P1-P3/D1-D3 라벨 체계는 실사용자용 공개 트래커가 아니라 팀 내부 구조화 도구.
- **디스코드도 비공개 문의가 아님.** 공식 초대 링크가 바로 공개 포럼 채널("🔥 문제 제보", Discord forum 채널 타입)로 연결됨 — 모든 문제 제보가 서버 멤버 전원에게 공개되는 구조. 별도 Fider 기반 공개 피드백 보드는 레포는 존재하나(KimuSoft/fider) 실제 라이브 운영 여부는 확인 못함.
- **함의**: 무료 취미 도구에겐 "공개 제보 → 중복 처리·커뮤니티 효과"가 합리적이지만, 정산/결제/계정처럼 민감한 문의가 있는 한줄 같은 상업 서비스엔 그대로 적용 불가. 일반 버그/기능요청은 공개, 계정·정산은 비공개 1:1로 채널을 분리하는 설계가 필요.

출처: GitHub API(`repos/KimuSoft/muvel-public/issues`), `discord.com/api/invites/jAbqy6JXsk?with_counts=true`

### 한줄에 대한 함의 (미결 — 다음 스펙 작업 인풋)

- 한줄이 노릴 대상은 뮤블 "현재 위치"가 아니라 펜시브가 뮤블을 공격하는 방식(AI 보조 + 검증된 프로 타겟)에 더 가까움.
- 한줄 자체 에디터가 필요하며, 뮤블(.muvl/.mvle/.mvlm)·펜시브 등 경쟁 도구의 산출물을 가져와 한줄 자체 포맷 또는 epub으로 변환하는 가져오기/내보내기 계층이 요구사항으로 식별됨 — 아직 스펙 미착수.

## 방법론 노트

deep-research 워크플로 실행 중 최초 run(wf_e9cfdfff-35e)의 synthesis 단계가 placeholder 값을 반환하는 오류가 있어, synthesis 프롬프트에 "플레이스홀더 금지" 지시를 추가하고 동일 run을 재실행(캐시된 99개 호출 재사용, synthesis만 재실행)하여 위 결과를 확보함. Raw 워크플로 결과와 전체 로그는 `/private/tmp/claude-501/-Users-daviy-Developer-hanjul-ide/9771053a-c9fd-47d4-a124-b7b8920c5dfe/tasks/wryfq2n4x.output` (세션 종료 시 소멸되는 임시 경로이므로 본 문서가 정본).
