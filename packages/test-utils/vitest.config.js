// @hanjul/test-utils 자체 테스트 설정 — 자기 vitest.shared.js 를 스프레드해서
// (다른 패키지들이 쓰는 것과 동일한 조각을) 자체 검증(dogfooding)한다.
import { defineConfig } from 'vitest/config';

import { sharedTestConfig } from './vitest.shared.js';

export default defineConfig({
  // JSX 리터럴(renderWithProviders.test.jsx 등)을 쓰는 자체 테스트가 있는데, web/potato 처럼
  // vite.config.js 의 plugins:[react()] 를 함께 쓰는 게 아니라 이 패키지만의 독립 vitest.config.js
  // 라서 JSX 자동 런타임을 직접 지정해야 한다 (안 하면 esbuild 기본(classic)이 걸려
  // "React is not defined").
  esbuild: { jsx: 'automatic' },
  test: {
    ...sharedTestConfig,
    include: ['src/**/*.test.{js,jsx}'],
  },
});
