// authFixture — createAuthContext() 의 useAuthContext() 리턴값(packages/lib/src/createAuthContext.jsx)
// 모양을 흉내낸 고정값. web/potato 테스트가 AuthContext 를 vi.mock 할 때 값 팩토리로 쓴다.
//
// ⚠️ vi.mock 호이스팅 제약: 이 모듈은 "값 팩토리"만 제공한다. vi.mock() 호출 자체를
// 헬퍼 함수로 감싸지 마라 — vitest 의 vi.mock 호이스팅은 테스트 파일에 직접 쓰인 리터럴에만
// 적용된다. 감싸는 순간(예: `mockAuth(overrides)` 가 내부에서 vi.mock 을 호출하는 식) 호이스팅이
// 안 먹혀 조용히 깨진다(모듈이 실제 구현으로 로드된 뒤에야 mock 이 걸림). 반드시 테스트 파일에서
// `vi.mock('...AuthContext', () => ({ useAuthContext: () => authFixture({ ... }) }))` 형태로
// 직접 호출할 것.
import { vi } from 'vitest';

/**
 * @param {object} [overrides]
 * @returns {{ user: object|null, login: Function, logout: Function, loading: boolean }}
 */
export function authFixture(overrides = {}) {
  return {
    user: null,
    login: vi.fn(),
    logout: vi.fn(),
    loading: false,
    ...overrides,
  };
}
