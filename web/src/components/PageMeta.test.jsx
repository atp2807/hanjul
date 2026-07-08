import { render } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { PageMeta } from './PageMeta';

// React 19 는 <title>/<meta> 를 컴포넌트 트리 어디서든 렌더하면 자동으로 document.head 로
// hoist 한다 — 이 테스트는 jsdom 에서 그 hoist 가 실제로 일어나는지 검증한다.
describe('PageMeta', () => {
  it('title 렌더 시 document.title 이 갱신된다 (React 19 <title> hoist)', () => {
    render(<PageMeta title="테스트책 — 한줄" description="책 설명" />);
    expect(document.title).toBe('테스트책 — 한줄');
  });

  it('og/twitter 메타가 head 에 반영된다', () => {
    render(
      <PageMeta
        title="표지책 — 한줄"
        description="요약 설명"
        image="https://cdn.hanjul.io/cover.png"
        url="https://www.hanjul.io/books/abc-123"
      />
    );
    // <head>의 <meta> 는 role/label이 없어 RTL 접근성 쿼리(getByRole 등)로 표현할 대상이
    // 아니다 — document.querySelector 잔존은 의도적(testing-library/no-node-access 불가피
    // 케이스, BrandMark.test.jsx의 선례와 동일한 예외).
    expect(document.querySelector('meta[name="description"]')?.getAttribute('content')).toBe('요약 설명');
    expect(document.querySelector('meta[property="og:title"]')?.getAttribute('content')).toBe('표지책 — 한줄');
    expect(document.querySelector('meta[property="og:description"]')?.getAttribute('content')).toBe('요약 설명');
    expect(document.querySelector('meta[property="og:image"]')?.getAttribute('content')).toBe(
      'https://cdn.hanjul.io/cover.png'
    );
    expect(document.querySelector('meta[property="og:url"]')?.getAttribute('content')).toBe(
      'https://www.hanjul.io/books/abc-123'
    );
    expect(document.querySelector('meta[name="twitter:card"]')?.getAttribute('content')).toBe(
      'summary_large_image'
    );
    expect(document.querySelector('meta[name="twitter:image"]')?.getAttribute('content')).toBe(
      'https://cdn.hanjul.io/cover.png'
    );
  });

  it('props 가 없어도 크래시 없이 렌더된다 (선택 필드 전부 옵셔널)', () => {
    expect(() => render(<PageMeta />)).not.toThrow();
  });
});
