// 한줄 모노레포 프론트 lint — eslint 9 flat config. web·potato·packages 공통.
import js from '@eslint/js';
import react from 'eslint-plugin-react';
import reactHooks from 'eslint-plugin-react-hooks';
import globals from 'globals';
import vitest from '@vitest/eslint-plugin';
import testingLibrary from 'eslint-plugin-testing-library';
import playwright from 'eslint-plugin-playwright';

// packages/* 는 헥사고날 경계상 web·potato(앱 레이어)에 의존 불가 — 순수 라이브러리로 유지.
const noAppLayerImportPatterns = [
  { group: ['**/web/**'], message: 'packages/* 는 web 에 의존 불가 — 헥사고날 경계 위반(앱→라이브러리 방향만 허용)' },
  { group: ['**/potato/**'], message: 'packages/* 는 potato 에 의존 불가 — 헥사고날 경계 위반(앱→라이브러리 방향만 허용)' },
];

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
      '**/.venv/**', // Python venv 안의 서드파티 JS(pywebview 등) — 린트 대상 아님(gitignore라 CI엔 없지만 로컬 일치)
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
      'react/no-danger': 'error', // dangerouslySetInnerHTML 금지 (XSS 회귀가드)
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
  {
    // vitest 단위/컴포넌트 테스트 — vitest recommended + testing-library(react) + 명시 규칙.
    files: ['**/*.test.{js,jsx}'],
    plugins: { vitest, 'testing-library': testingLibrary },
    rules: {
      ...vitest.configs.recommended.rules,
      ...testingLibrary.configs['flat/react'].rules,
      'vitest/no-focused-tests': 'error', // it.only/describe.only 커밋 방지
      'vitest/no-disabled-tests': 'warn', // it.skip 등 — 존재 자체는 허용, 누적 확인용
      'testing-library/no-wait-for-multiple-assertions': 'error',
      'testing-library/no-unnecessary-act': 'error',
      // testing-library flat/react 기본은 error지만, 기존 테스트 11개 파일에 걸쳐 광범위 위반
      // (container.querySelector 직접 접근 등) — 전면 리팩터는 별도 후속 작업으로 미루고 warn 완화.
      'testing-library/no-container': 'warn',
      'testing-library/no-node-access': 'warn',
      'testing-library/prefer-find-by': 'warn',
      'testing-library/prefer-presence-queries': 'warn',
    },
  },
  {
    // playwright E2E — flat/recommended + 명시 규칙(느린/깜빡이는 테스트 패턴 회귀가드).
    files: ['**/e2e/**/*.js'],
    plugins: { playwright },
    rules: {
      ...playwright.configs['flat/recommended'].rules,
      'playwright/no-focused-test': 'error', // test.only 커밋 방지
      'playwright/no-wait-for-timeout': 'error', // 하드코딩 sleep 대신 조건 대기
      'playwright/no-networkidle': 'error', // networkidle은 SPA에서 신뢰 불가
    },
  },
  {
    // 헥사고날 경계: packages/* 는 앱(web/potato)에 의존 불가.
    files: ['packages/**/*.{js,jsx}'],
    rules: {
      'no-restricted-imports': ['error', { patterns: noAppLayerImportPatterns }],
    },
  },
  {
    // packages/doc/src 는 프레임워크 무소속 순수 엔진(.js) — react 금지 + API 원본 필드명 직접 사용 금지.
    // (react 래퍼는 DocEditor.jsx/DocReader.jsx 에만 존재 — .jsx 는 이 블록 대상 아님)
    // no-restricted-imports 는 파일당 마지막 매치 블록이 통째로 덮어쓰므로, 위 packages/**
    // 블록의 web/potato 금지도 여기 patterns 로 함께 명시해 유지한다.
    files: ['packages/doc/src/**/*.js'],
    rules: {
      'no-restricted-imports': [
        'error',
        {
          paths: [
            { name: 'react', message: 'packages/doc/src 는 프레임워크 무소속 순수 엔진 — react는 .jsx 래퍼에서만' },
          ],
          patterns: noAppLayerImportPatterns,
        },
      ],
      'no-restricted-syntax': [
        'error',
        {
          selector: 'Identifier[name=/^(sourceHash|createdAt|updatedAt|pageSize|displayUrl|thumbUrl|contentType)$/]',
          message:
            'API 원본 필드명 직접 사용 금지 — docs.js 경계 매핑 우회 의심. web/src/services/api/docs.js 에서 도메인 이름으로 매핑 후 전달하세요.',
        },
      ],
    },
  },
];
