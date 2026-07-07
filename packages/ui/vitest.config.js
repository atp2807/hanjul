import { defineConfig } from 'vitest/config';

import { sharedTestConfig } from '@hanjul/test-utils/vitest-shared';

export default defineConfig({
  // 이 패키지엔 web/potato 처럼 plugins:[react()] 를 주는 vite.config.js 가 없으므로,
  // 컴포넌트(.jsx) 렌더 테스트를 위해 JSX 자동 런타임을 직접 지정한다
  // (안 하면 esbuild 기본(classic)이 걸려 "React is not defined").
  esbuild: { jsx: 'automatic' },
  test: {
    ...sharedTestConfig,
  },
});
