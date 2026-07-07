// @hanjul/doc React 래퍼(DocEditor/DocReader) 동작 테스트 — 실제 코어 마운트.
// ref 1회 마운트(DOM-as-state), StrictMode 이중 마운트 멱등, apiBase 이미지 매핑을 잠근다.
// (다른 페이지 테스트는 이 래퍼를 stub 으로 mock 하지만, 여기선 실물을 렌더한다.)
import { StrictMode } from 'react';
import { render } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { DocEditor, DocReader } from '@hanjul/doc';

const IMG_CANON = '<article data-juldoc="1"><p>본문</p><img src="/media/k1" alt="i"></article>';

describe('DocEditor 래퍼', () => {
  it('StrictMode 이중 마운트에도 툴바/에디터가 하나씩(cleanup 멱등)', () => {
    const controlRef = { current: null };
    const { container } = render(
      <StrictMode><DocEditor html={IMG_CANON} apiBase="" controlRef={controlRef} /></StrictMode>,
    );
    expect(container.querySelectorAll('.juldoc-toolbar').length).toBe(1);
    expect(container.querySelectorAll('article.juldoc-editor').length).toBe(1);
    expect(typeof controlRef.current.save).toBe('function');
    expect(typeof controlRef.current.isDirty).toBe('function');
  });

  it('apiBase 로 정본 img src 를 표시경로로 매핑해 마운트', () => {
    const { container } = render(<DocEditor html={IMG_CANON} apiBase="" />);
    expect(container.querySelector('article img').getAttribute('src')).toBe('/api/media/k1');
  });

  it('unmount 시 컨트롤러 해제', () => {
    const controlRef = { current: null };
    const { unmount, container } = render(<DocEditor html={IMG_CANON} apiBase="" controlRef={controlRef} />);
    expect(container.querySelector('.juldoc-toolbar')).not.toBeNull();
    unmount();
    expect(controlRef.current).toBeNull();
  });
});

describe('DocReader 래퍼', () => {
  // jsdom canvas 부재 회피 위해 img(fixedHeight) 블록만 사용.
  it('StrictMode 이중 마운트에도 .juldoc-reader 하나 + apiBase 이미지 매핑', () => {
    const html = '<article data-juldoc="1"><img src="/media/p1" alt="p"></article>';
    const { container } = render(
      <StrictMode><DocReader html={html} apiBase="https://api.hanjul.io" /></StrictMode>,
    );
    expect(container.querySelectorAll('.juldoc-reader').length).toBe(1);
    expect(container.querySelector('img').getAttribute('src')).toBe('https://api.hanjul.io/api/media/p1');
  });
});
