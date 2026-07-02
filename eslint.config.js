// 한줄 모노레포 프론트 lint — eslint 9 flat config. web·potato·packages 공통.
import js from '@eslint/js';
import react from 'eslint-plugin-react';
import reactHooks from 'eslint-plugin-react-hooks';
import globals from 'globals';

const testGlobals = {
  describe: 'readonly',
  it: 'readonly',
  test: 'readonly',
  expect: 'readonly',
  vi: 'readonly',
  beforeEach: 'readonly',
  afterEach: 'readonly',
  beforeAll: 'readonly',
  afterAll: 'readonly',
};

export default [
  {
    ignores: [
      '**/dist/**',
      '**/node_modules/**',
      'backend/**', // Python — ruff 담당 (.venv 서드파티 JS 포함 제외)
      'packages/ui/ds-bundle/**',
      'packages/ui/.ds-sync/**',
      'packages/ui/.design-sync/**',
      'web/playwright-report/**',
      'web/test-results/**',
      '**/coverage/**',
      '**/*.d.ts',
    ],
  },
  js.configs.recommended,
  {
    files: ['**/*.{js,jsx,mjs}'],
    languageOptions: {
      ecmaVersion: 2023,
      sourceType: 'module',
      globals: { ...globals.browser, ...globals.node },
      parserOptions: { ecmaFeatures: { jsx: true } },
    },
    plugins: { react, 'react-hooks': reactHooks },
    rules: {
      'react/jsx-uses-vars': 'error', // JSX에서 쓰는 컴포넌트 import를 미사용으로 오탐 방지
      'react-hooks/rules-of-hooks': 'error',
      'react-hooks/exhaustive-deps': 'warn',
      'no-unused-vars': ['warn', { argsIgnorePattern: '^_', varsIgnorePattern: '^_' }],
      'no-empty': ['error', { allowEmptyCatch: true }],
    },
  },
  {
    files: ['**/*.test.{js,jsx}', '**/e2e/**/*.js', '**/test/**/*.{js,jsx}'],
    languageOptions: { globals: { ...globals.node, ...testGlobals } },
  },
];
