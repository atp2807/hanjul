# 테스트 아키텍처 가이드

> 정본. 새 테스트를 어디에 놓을지, 어떤 픽스처/헬퍼를 재사용할지 판단이 서지 않으면 이 문서부터 본다.
> 조사일: 2026-07-07 (아래 카탈로그 항목은 전부 실제 파일 대조 완료 — grep/Read 재확인 후 반영).

## 1. 개요 — 4계층 + 기준선

한줄은 4계층으로 테스트를 나눈다: **백엔드 단위/통합**(pytest) · **프론트 컴포넌트**(vitest) ·
**브라우저 E2E**(Playwright, web) · **조판 실측 E2E**(Playwright, packages/doc). 계층마다
"무엇을 실제로 띄우는가"가 다르므로 배치 기준도 계층별로 별도(§2.1, §3.3, §4.2).

| 계층 | 도구 | 통과 수 | 비고 |
|---|---|---|---|
| 백엔드 단위/통합 | pytest (`.venv`, 3.14) | **854 passed, 3 skipped** | ruff(src+tests)·lint-imports(4 계약, 0 위반)·lint_naming.py 전부 그린 |
| 프론트 컴포넌트 — web | vitest | **308 passed** (62파일) | |
| 프론트 컴포넌트 — potato | vitest | **29 passed** (6파일) | |
| 프론트 컴포넌트 — packages/doc | vitest | **92 passed** | |
| 프론트 컴포넌트 — packages/test-utils | vitest | **8 passed** | |
| 프론트 컴포넌트 — packages/lib | vitest | **36 passed** | |
| 프론트 컴포넌트 — packages/ui | vitest | **1 passed** | |
| 브라우저 E2E — web (Playwright) | Playwright | **72 passed** | 실 백엔드(28100)+프론트(35200)+postgres(`hanjul_e2e`) |
| 조판 실측 E2E — packages/doc | Playwright | **14 passed** | 백엔드/DB 불요, chromium 캔버스/DOM 실측 |
| eslint | eslint 9 flat | **0 errors** | 경고 다수 — 대부분 `testing-library/no-container`·`no-node-access`·`prefer-find-by`·`prefer-presence-queries` 계열(§5), 기존 11개 파일 한정, 후속 정리 대상 |

**e2e 합계 = 72 + 14 = 86.**

⚠️ **CI 갭 — 정직하게 기록**: `.github/workflows/ci.yml`의 `frontend` 잡은
`npm run test -w web`·`-w potato`·`-w packages/doc`만 명시 실행한다. `packages/lib`·
`packages/ui`·`packages/test-utils`는 각자 `test` 스크립트(vitest run)가 있고 로컬에서
위 수치로 통과하지만, **CI가 아직 이 세 패키지를 명시적으로 실행하지 않는다**(루트에 이를
묶는 `vitest.workspace.js`나 `npm test` 애그리게이터도 없음). 회귀가 CI에서 안 잡힐 수 있는
사각지대 — 코드/설정 변경은 이 문서의 범위 밖이라 여기서는 사실만 기록한다.

## 2. 백엔드 테스트 가이드

### 2.1 배치 결정트리

새 테스트를 쓸 때 아래 순서로 판단한다 (`backend/tests/` 하위 디렉토리 = 판단 결과):

```
DB(SQLAlchemy 세션·실 SQL)가 필요한가?
├─ 예  → tests/integration/  (SQLite in-memory 실 엔진, conftest.py 공용 픽스처 §2.2)
└─ 아니오
   실 리포지토리 대신 Fake로 대체 가능한 유스케이스/서비스 레이어인가?
   ├─ 예  → tests/features/<feature>/  (인메모리 Fake repo, tests/fixtures/fake_*.py)
   └─ 아니오
      순수 로직(도메인 함수·엔진 변환·계산)이고 DB/HTTP 모두 불필요한가?
      ├─ 예  → tests/engine/  (예: epub.py·onix.py·settlement.py·doc/*)
      └─ 아니오
         실 네트워크 + 실 자격증명이 필요한가(샌드박스 API 등)?
         └─ 예  → @pytest.mark.live + skipif(환경변수) — 평소 CI/로컬은 skip
                  (예: tests/integration/test_toss_live.py, RUN_TOSS_LIVE=1)
```

`tests/meta/`는 위 4갈래와 별개 — 코드가 아니라 **레포 상태 자체**(schema_translate_map
동기화, OpenAPI 스냅샷)를 검증하는 정적 가드다(§5).

### 2.2 conftest 픽스처 카탈로그 (`tests/integration/conftest.py`)

실제 시그니처 (94-132행대 발췌, 파일: `backend/tests/integration/conftest.py`):

| 픽스처 | 시그니처/반환 | 용도 |
|---|---|---|
| `sessionmaker` | `async_sessionmaker` 콜러블 | SQLite in-memory 엔진(`schema_translate_map`에 `pub/usr/bill/dist/commu/potato/doc` 전부 None 매핑) + `Base.metadata.create_all` |
| `social_profile` | `SocialProfile("GOOGLE", "test-sub", "test@x.com", "테스트유저")` | 로그인 기본 프로필. 다른 provider/유저 필요하면 테스트 파일에서 **동일 이름으로 재정의**(오버라이드) |
| `order_gateway` | `FakeGateway(ok=True)` | 결제 게이트웨이 대역, 기본 항상 승인. 실패 시나리오는 로컬 재정의 |
| `app_db` | `sessionmaker` 반환(콜러블) | `get_session` + `get_auth_service`(FakeProvider) 오버라이드. `async with app_db() as s:` 로 직접 시딩/검증 가능 |
| `app_db_orders` | `app_db` 확장 | `app_db` + `get_order_service`(`OrderService(SqlOrderRepository, order_gateway, SqlBookPricing)`) 오버라이드 |
| `app_db_potato` | `sessionmaker` 반환 | `get_session` + `get_potato_session` 오버라이드 — potato(운영자) 엔드포인트 테스트용 |
| `client` | `httpx.AsyncClient` (ASGITransport) | `app_db` 오버라이드가 걸린 클라이언트 — 고객 엔드포인트 E2E(auth/books 등) |
| `client_orders` | `httpx.AsyncClient` | `app_db_orders` 오버라이드가 걸린 클라이언트 — 주문/결제 흐름 포함 |

주의: pytest는 테스트 모듈에 정의된 동일 이름 픽스처를 conftest보다 우선시킨다 — 기존
34개 파일이 각자 로컬 `app_db`를 정의해도 이 conftest와 충돌 없이 공존한다. 신규 테스트가
매번 보일러플레이트를 다시 쓰지 않게 하는 것이 이 카탈로그의 목적.

### 2.3 헬퍼 함수 카탈로그 (`tests/integration/*_helpers.py`)

**`auth_helpers.py`** — 소셜 콜백(302 리다이렉트) 처리:
```python
async def login_token(client, provider: str, code: str) -> tuple[str, bool]:
    """콜백 → 302. Location fragment 에서 (token, is_new) 추출."""

async def login_account(client, provider: str, code: str) -> tuple[str, dict]:
    """로그인 후 /me 로 계정 정보까지 → (token, account_dict). (get_session 오버라이드 필요)"""

def fresh_account_auth(role: str = "READER") -> dict:
    """OAuth 왕복 없이 새 UUID로 토큰 직접발급 — 헤더 dict 바로 반환."""
```

⚠️ **함정(2026-07-08 실사고, `lr-747a0b49`)**: `login_account`/`login_token`의 `code` 인자는 **계정 구분자가 아니다** — `FakeProvider`는 실제 OAuth와 마찬가지로(같은 사람이 재로그인해도 code는 매번 다름) code 값과 무관하게 `social_profile` fixture 하나만 고정 반환한다. 그래서 `login_account(..., "a")`와 `login_account(..., "b")`를 같은 테스트 파일에서 불러도 **전부 같은 계정**이다. 한 테스트 **함수** 안에서 진짜 서로 다른 계정(작가 vs 제3자 vs 구매자 등 접근제어 테스트)이 필요하면 `login_account` 대신 **`fresh_account_auth()`**를 쓸 것 — 매 호출이 새 UUID라 헷갈릴 여지가 없다.

**`book_helpers.py`** — 책 생성·원고 import·즉시출판:
```python
async def create_book(client, headers=None, *, title: str, kind: str = "BOOK") -> str:
    """POST /api/books → bookId."""

async def import_raw(client, book_id: str, raw_text: str, headers=None) -> dict:
    """POST /api/books/{id}/import → {chapterId, blockCount}."""

async def publish_priced_book(
    client, headers, *, title: str, price: int, raw_text: str = "1\n\n2\n\n3"
) -> str:
    """생성 → import → 가격설정 → 즉시출판(publish-now, 심사 생략)까지 한 번에. bookId 반환."""
```

**`order_helpers.py`** — 주문 생성·결제확인 (청약철회 동의 §17⑥ 필수, 금액은 서버 도출):
```python
async def buy_book(client, headers, book_id: str, *, channel: str = "SELF", pg_tx_id: str = "test-tx") -> str:
    """POST /api/orders(withdrawalConsent=True) → POST /api/orders/{id}/confirm. order_id 반환."""
```

### 2.4 Fake repo 규칙

- 파일명 `fake_<feature>_repo.py`, 클래스명 `Fake<Feature>Repository` (예: `FakeBookRepository`,
  `FakeCatalogRepository`, `FakeCampaignRepository`, `FakeReportRepository`, `FakePayoutRepository`).
  단, 이름이 리포지토리 이상을 대역하는 경우는 역할 그대로: `fake_order_repo.py`는
  `FakeGateway`·`FakePricing`·`FakeOrderRepository` 셋을 담는다.
- **가변 mutation** — 내부 상태는 `dict`(예: `self.by_cred`, `self.accounts`, `self.books`)에
  직접 담고 메서드가 그 자리에서 갱신한다. 불변 갱신·이벤트소싱 패턴 없음 — 테스트 코드는
  최대한 단순하게.
- **공통 베이스 클래스 없음** — 모든 Fake repo는 대상 Protocol(예:
  `src.features.accounts.domain.models.AccountRepository`)을 **구조적으로**(덕 타이핑) 만족할
  뿐, 상속하지 않는다. 실제로 파일 간 공유되는 표면은 "id로 dict에서 찾아 반환" 한 줄 패턴뿐이라
  베이스 클래스를 두면 오히려 과추상화 — 그래서 의도적으로 두지 않았다.
- ⚠️ **`fake_account_repo.py`(auth, 단수) vs `fake_accounts_repo.py`(accounts, 복수) 구분**:
  - `fake_account_repo.py` → `FakeAccountRepository` + `FakeProvider` — **auth** 피처(소셜
    로그인 자격증명, `find_by_credential`/`create_with_credential`) 전용.
  - `fake_accounts_repo.py` → `FakeAccountsRepository` — **accounts** 피처(프로필 조회/이름
    일괄조회/탈퇴, `get`/`exists`/`names_for`/`set_status`/`withdraw`) 전용. 파일 상단에
    "auth의 기존 FakeAccountRepository(단수)와 이름이 겹쳐 복수형으로 분리했다"는 주석이
    명시돼 있다 — **새 코드에서 이 둘을 헷갈리면 안 된다.**
- 예외(juldoc 이식) — `fake_doc_repo.py`는 `FakeDocumentRepo`/`FakeShareRepo`로 `Repository`가
  아닌 `Repo` 축약을 쓴다. 이식 원본 컨벤션을 그대로 둔 것으로 신규 파일에서 따라 하지 말 것
  (§2.5 참조).

### 2.5 코딩 컨벤션

- **함수형** — 클래스가 아니라 `async def test_...` 평범한 함수로 작성(단, Fake repo 자체는
  상태를 담아야 하니 클래스).
- **한글 docstring** — 파일 최상단 모듈 docstring + 헬퍼 함수 docstring 모두 한글.
- **상단 import** — 함수 내부가 아니라 파일 맨 위에 전부 모아 선언(지연 import 지양).
  단 `tests/integration/conftest.py`는 `settings.DEBUG = False`를 `main` import보다 먼저
  실행해야 해서 일부 import를 `# noqa: E402`로 뒤로 미룬 예외가 있다 — 이유가 코드 주석에
  명시돼 있다.
- **섹션 배너** — `# ── 제목 ──────` 형태 주석으로 파일 내부를 구획(예:
  `fake_accounts_repo.py`의 `# ── Fake 리포지토리 ──`).
- ⚠️ **예외 — juldoc 이식분은 안 고침**: `backend/tests/engine/doc/`와
  `backend/tests/features/doc/`는 juldoc(독립 문서플랫폼) 원본을 그대로 옮겨온 코드라
  **클래스 기반(`class TestUpload:` 등) + 영문 docstring** 스타일을 그대로 유지한다. 새
  테스트를 이 두 디렉토리에 추가할 때는 위 함수형/한글 규칙이 아니라 **그 디렉토리의 기존
  스타일**을 따른다. 다른 모든 디렉토리는 함수형+한글이 정본.

## 3. 프론트 테스트 가이드

### 3.1 `@hanjul/test-utils` 카탈로그 (`packages/test-utils/src/index.js` 배럴)

```js
export { renderWithProviders } from './renderWithProviders.jsx';
export { authFixture } from './authFixture.js';
export { mockApiClient } from './mockApiClient.js';
export { httpError } from './httpError.js';
export { docStubs } from './docStubs.jsx';
```

| export | 시그니처 | 용도 |
|---|---|---|
| `renderWithProviders(ui, { path, at = '/', router = true } = {})` | `RenderResult` | `MemoryRouter`(+선택적 `<Routes><Route>`)로 감싸 렌더. `useParams`/`useNavigate` 쓰는 페이지 컴포넌트용. `router: false`면 그냥 `render(ui)`. |
| `authFixture(overrides = {})` | `{ user: null, login: fn, logout: fn, loading: false, ...overrides }` | `createAuthContext()`의 `useAuthContext()` 리턴 모양을 흉내낸 값 팩토리. |
| `mockApiClient()` | `{ get, post, put, del, upload, download }` (전부 `vi.fn()`) | `createApiClient()` 리턴 모양의 목. `mockResolvedValue`/`mockRejectedValue`로 세팅. |
| `httpError(status, detail = null)` | `Error & { status, detail }` | `packages/lib/src/apiClient.js`의 `toError()`가 만드는 실제 에러 모양 재현. |
| `docStubs()` | `{ DocReader, DocEditor }` | `@hanjul/doc`의 `DocReader`(html 그대로 렌더, `data-testid="doc-reader"`)/`DocEditor`(`data-testid="doc-editor"`, 저장 버튼 클릭 시 `onSave(html)`) 스텁. |

예제(`web/src/components/Header.test.jsx`):
```js
import { renderWithProviders, authFixture } from '@hanjul/test-utils';
import * as authCtx from '../auth/AuthContext';

vi.mock('../auth/AuthContext');
// ...
authCtx.useAuth.mockReturnValue(authFixture({ user: null, logout: vi.fn() }));
renderWithProviders(<Header />);
```

### 3.2 ⚠️ vi.mock 호이스팅 경고

`@hanjul/test-utils`는 **"값 팩토리"만 제공한다.** `vi.mock()` 호출 자체를 헬퍼 함수로
감싸면 안 된다 — vitest의 `vi.mock` 호이스팅은 **테스트 파일에 직접 쓰인 리터럴**에만
적용된다. 감싸는 순간(예: 헬퍼가 내부에서 `vi.mock`을 대신 호출) 호이스팅이 안 먹혀 조용히
깨진다(모듈이 실제 구현으로 먼저 로드된 뒤에야 mock이 걸림 — 에러 없이 그냥 실패).

**틀린 예** — 절대 이렇게 만들지 말 것:
```js
// ❌ test-utils 안에 이런 헬퍼를 추가하면 안 됨
export function mockAuth(overrides) {
  vi.mock('../auth/AuthContext', () => ({ useAuth: () => authFixture(overrides) }));
}
// 테스트 파일에서: mockAuth({ user: null })  ← 호이스팅 안 됨, 조용히 깨짐
```

**올바른 예** — 테스트 파일에서 `vi.mock`을 직접, 값 팩토리만 가져다 쓴다(실제 코드,
`web/src/components/MobileTabBar.test.jsx:7`):
```js
import { authFixture } from '@hanjul/test-utils';

vi.mock('../auth/AuthContext', () => ({ useAuth: () => authFixture({ user: null }) }));
```
`docStubs`도 동일 원칙(`web/src/pages/DocSharePage.test.jsx:9`):
```js
vi.mock('@hanjul/doc', () => docStubs());
```

### 3.3 배치 결정트리

```
페이지 컴포넌트(라우트에 물리는 컴포넌트)?  → src/pages/*.test.jsx   (renderWithProviders 사용)
API 클라이언트 함수(services/api/*.js)?      → src/services/api/*.test.js
여러 앱이 공유하는 순수 로직/컴포넌트?        → packages/<pkg>/src/*.test.{js,jsx}
```
`web`·`potato` 양쪽에서 쓰이거나 향후 쓰일 가능성이 있는 로직/컴포넌트는 처음부터
`packages/lib`(로직)나 `packages/ui`(컴포넌트)에 두는 것을 우선 검토 — 이미 있는 것을 각
앱에 다시 베끼지 않는다.

### 3.4 vitest 공유설정(`vitest.shared.js`) 사용법

`packages/test-utils/vitest.shared.js`는 `environment: 'jsdom'`·`globals: true`·
`setupFiles: ['@hanjul/test-utils/setup']`만 담은 "정말 공통인 것"만의 조각이다. coverage 등
앱/패키지별 고유 설정은 각자 `vite.config.js`/`vitest.config.js`에 남긴다.

`package.json`의 `exports`가 `"./vitest-shared": "./vitest.shared.js"`로 매핑돼 있어
import 경로는 하이픈(`vitest-shared`)이지만 실제 파일명은 점(`vitest.shared.js`)이다 —
헷갈리지 말 것.

```js
// web/vite.config.js, potato/vite.config.js, packages/{ui,lib,test-utils}/vitest.config.js
import { sharedTestConfig } from '@hanjul/test-utils/vitest-shared';

export default defineConfig({
  test: {
    ...sharedTestConfig,
    exclude: ['**/node_modules/**', '**/e2e/**'], // web은 e2e 디렉토리 추가 제외
    coverage: { /* 앱별 고유 설정 */ },
  },
});
```

## 4. e2e(Playwright) 가이드

### 4.1 `web/e2e/helpers.js` 카탈로그

```js
async function login(page, email, name = '테스트작가')
// test-login 우회로 브라우저 세션 로그인 → '로그아웃' 버튼 보일 때까지 대기.

async function tokenFor(request, email, name = '테스트작가'): Promise<string>
// test-login 302 응답의 location fragment(#token=...)에서 JWT만 뽑는다(UI 없이 API 인증용).

async function authorSession(request, email, name = '테스트작가'):
  Promise<{ authorId: string, auth: { Authorization: string }, token: string }>
// 토큰 발급 + /api/me 조회까지 일괄 — authorId가 필요한 시나리오(작가 팔로우 등)에 사용.

async function seedBook(request, {
  authorEmail, auth, title, rawText,
  price = null, category = null, publish = price !== null,
}): Promise<string>  // bookId
// 책 생성 → import → (가격) → (분류) → (발행) 순으로 시드. auth를 넘기면 같은 작가로
// 책 여러 권 시드할 때 토큰을 다시 안 딴다. price가 있는데 미출판 상태가 필요하면
// publish: false를 반드시 명시.

function uniqueEmail(label: string): string
// `${label}-${Date.now()}-${random}@e2e.hanjul.io` — 스위트 내 계정 충돌 방지.

async function seedPublishedBook(request, { authorEmail, title, price }): Promise<string>
// seedBook에 '# 1장\n\n본문입니다.' + publish:true 고정 위임 (소비자 구매 여정 전제 시드).
```

기존 spec 파일 곳곳에 흩어져 있던 로컬 `tokenFor`/`seedDraftBook`/`seedAuthorWithDraft`/
`seedLongFreeBook`/`seedWithCategory` 변형들을 이 6개로 통합했다 — **새 spec은 로컬 재발명
대신 이 헬퍼를 가져다 쓴다.**

### 4.2 packages/doc/e2e vs web/e2e 선택 기준

| | `web/e2e/` | `packages/doc/e2e/` |
|---|---|---|
| 백엔드/DB | 필요 (28100 + `hanjul_e2e` postgres, `global-setup.js`가 매 실행 재생성+마이그레이션) | **불필요** — `@hanjul/doc` 코어 단독 |
| 무엇을 검증 | 로그인·구매·출판 등 앱 전체 플로우(HTTP 왕복 포함) | 조판(typeset) 실측 — 실제 chromium 캔버스/DOM 측정 |
| 서버 | `web/playwright.config.js`의 `webServer` 배열 3종(백엔드 uvicorn·sync-server·vite dev) | `vite.harness.config.js`가 서빙하는 정적 하니스(`doc-typeset-harness.html`) 하나 |
| 병렬성 | `fullyParallel: false`, `workers: 1` — 단일 DB 공유라 직렬 | `fullyParallel: true` — DB/외부상태 공유 없음 |
| 판단 기준 | **DB에 쓰고 읽는 상태**나 **여러 API 왕복**이 필요하면 이쪽 | **DB/백엔드 없이 프론트 로직/렌더만** 검증하면 이쪽(조판처럼 캔버스 픽셀 단위 실측이 필요한 것도 포함) |

CI 배치도 이를 반영: 조판 e2e는 무거운 `e2e` 잡이 아니라 `frontend` 잡에 얹혀 있다(백엔드
기동이 불필요해 가볍기 때문, `.github/workflows/ci.yml` 45-49행).

### 4.3 데이터 격리 / 셀렉터 관례

- **데이터 격리**: `uniqueEmail(label)` 사용을 권장 — 고정 이메일을 재사용하면 표시
  이름·팔로우 상태 등이 스위트 간에 오염될 수 있다. DB 자체는 `global-setup.js`가 매 실행
  전체 재생성(`dropdb`→`createdb`→`migrate.py`)하지만, 같은 실행 내 spec들끼리는
  이메일로 계정을 분리해야 한다.
- **셀렉터 관례**: 실사용 빈도 기준(`e2e/*.spec.js` 실측) `getByRole`(92건) >
  `getByTestId`(73건) > `getByText`(64건) > `getByLabel`(6건). Testing Library/Playwright
  권장 우선순위(role·label·text 우선, testid는 최후)를 지향하되, ProseMirror 에디터·캔버스
  조판처럼 접근성 트리로 잡기 어려운 대상은 `data-testid`를 적극 쓴다 — 두 관례가 혼재하는
  것이 정상이다.

## 5. 자동 가드 카탈로그

**import-linter 계약 4개** (`backend/pyproject.toml`, `[tool.importlinter]`, CI에서
`lint-imports`로 검사, 확정 사실: 4 kept 0 broken):
1. `features 헥사고날 레이어` — `src.features.*` 컨테이너 내부가
   presentation→infrastructure→application→domain 순서로만 의존 가능(layers 계약).
2. `domain 계층은 FastAPI/SQLAlchemy를 모른다` — `src.features.*.domain`에서 `fastapi`·
   `sqlalchemy` import 금지(forbidden 계약).
3. `application 계층은 FastAPI/SQLAlchemy를 모른다` — 위와 동일 취지, `application` 계층
   대상.
4. `engine은 features를 모른다` — `src.engine`에서 `src.features` import 금지. 엔진은
   feature 비의존 순수 모듈로 유지.

**eslint 테스트 플러그인 + 경계 규칙** (`eslint.config.js`, eslint 9 flat config):
- `@vitest/eslint-plugin`(`**/*.test.{js,jsx}`) — `vitest.configs.recommended` +
  `vitest/no-focused-tests: error`(`it.only` 커밋 방지) + `no-disabled-tests: warn`.
- `eslint-plugin-testing-library`(`flat/react`) — `no-wait-for-multiple-assertions: error`·
  `no-unnecessary-act: error`는 강제. `no-container`·`no-node-access`·`prefer-find-by`·
  `prefer-presence-queries`는 기존 11개 파일의 광범위 위반 때문에 **경고로 완화**돼 있음
  (§1 기준선의 "경고 다수"가 대부분 이것 — 후속 정리 대상).
- `eslint-plugin-playwright`(`**/e2e/**/*.js`) — `flat/recommended` +
  `no-focused-test: error`·`no-wait-for-timeout: error`(하드코딩 sleep 금지)·
  `no-networkidle: error`(SPA에서 신뢰 불가).
- **경계 규칙**: `packages/**/*.{js,jsx}`는 `no-restricted-imports`로 `**/web/**`·
  `**/potato/**` import 금지(라이브러리→앱 역참조 금지, 헥사고날 경계). `packages/doc/src/**/*.js`
  (순수 엔진, `.jsx` 래퍼 제외)는 추가로 `react` import 금지 + `no-restricted-syntax`로
  `sourceHash`/`createdAt`/`updatedAt`/`pageSize`/`displayUrl`/`thumbUrl`/`contentType` 같은
  API 원본 필드명 직접 사용 금지(`web/src/services/api/docs.js` 경계 매핑 우회 방지).

**`tests/meta/` 2종** (DB/네트워크 없이 레포 상태 자체를 정적 검증):
- `test_schema_translate_map.py` — 마이그레이션이 `CREATE SCHEMA`하는 스키마 목록과
  `tests/integration/conftest.py`의 `schema_translate_map` 키를 정적으로 대조, 양방향 누락 검출.
- `test_openapi_snapshot.py` — `app.openapi()` 결과를 `tests/fixtures/openapi_snapshot.json`과
  비교. ⚠️ **pydantic 버전 가드**: `.venv`(3.14)는 pydantic 2.13.x, `.venv312`(3.12, 런타임·
  마이그레이션·E2E·**CI 정본**)는 pydantic 2.9.x — JSON Schema 직렬화가 버전 간 미묘하게
  달라질 수 있어 스냅샷은 **pydantic 2.9(.venv312)에서만 생성·검증**하고 그 외 버전(즉 로컬
  `.venv`의 일반 `pytest -q`)에서는 `skipif`로 건너뛴다. 갱신 명령:
  `cd backend && .venv312/bin/python scripts/update_openapi_snapshot.py`.

**pre-commit(husky)** — **이미 존재한다**(`.husky/pre-commit`, 실제 내용):
```
npx lint-staged
cd backend && .venv/bin/python scripts/lint_naming.py && cd ..
node scripts/check-large-files.mjs
node scripts/check-secrets.mjs
```
`lint-staged`(루트 `package.json`)는 스테이징된 `*.{js,jsx}`에 `eslint --fix`, 스테이징된
`backend/**/*.py`에 `ruff check --fix`를 돌린다. `lint_naming.py`(§ CLAUDE.md 네이밍 게이트)·
대용량 파일 체크·시크릿 체크가 뒤따른다. 즉 pytest 전체 실행이나 import-linter, OpenAPI
스냅샷 검증까지는 pre-commit이 커버하지 않음 — 그건 CI(§6)가 최종 게이트다.

## 6. 기준선

§1의 표가 정본 기준선이다. **이 숫자는 낮아지면 안 된다** — PR/커밋으로 테스트 수가
줄었다면(스킵 추가 포함) 의도적 삭제인지 실수인지 반드시 확인할 것. 신규 기능은 테스트를
동반해 숫자를 늘리는 방향으로만 움직인다. 예외적으로 테스트를 삭제해야 한다면(중복 제거,
기능 자체 제거 등) 그 사유를 커밋 메시지에 명시한다.

## 7. `--no-verify` 정책

pre-commit(husky)은 **로컬 빠른 피드백**용이다(lint-staged·네이밍 린터·대용량/시크릿
체크, §5) — pytest 전체·import-linter·OpenAPI 스냅샷·Playwright는 돌리지 않는다. **CI가
최종 게이트**(`.github/workflows/ci.yml`의 backend/frontend/e2e 3잡, §1). 따라서:

- 긴급 상황(예: 하필 대용량 바이너리 오탐, 훅 자체 버그)에서 `git commit --no-verify`로
  pre-commit을 우회하는 것은 **허용**한다.
- 단, 우회했다면 **push 전에 반드시 CI 결과를 확인**할 것 — pre-commit이 잡았어야 할 문제가
  CI에서 뒤늦게 터지면 그만큼 되짚기 비용이 크다.
- 아키텍처 규칙(CLAUDE.md "Git Safety Protocol")에 따라 `--no-verify`는 사용자가 명시적으로
  요청한 경우에만 쓴다 — 임의로 훅을 건너뛰지 않는다.
