// @hanjul/doc React 래퍼(DocEditor/DocReader) 동작 테스트 — 실제 코어 마운트.
// ref 1회 마운트(DOM-as-state), StrictMode 이중 마운트 멱등, apiBase 이미지 매핑을 잠근다.
// (다른 페이지 테스트는 이 래퍼를 stub 으로 mock 하지만, 여기선 실물을 렌더한다.)
import { StrictMode } from 'react';
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { DocEditor, DocReader } from '@hanjul/doc';

const IMG_CANON = '<article data-juldoc="1"><p>본문</p><img src="/media/k1" alt="i"></article>';

describe('DocEditor 래퍼', () => {
  it('StrictMode 이중 마운트에도 툴바/에디터가 하나씩(cleanup 멱등)', () => {
    const controlRef = { current: null };
    render(
      <StrictMode><DocEditor html={IMG_CANON} apiBase="" controlRef={controlRef} /></StrictMode>,
    );
    // 툴바 중복 마운트 시 버튼도 중복되므로, 고유 버튼 1개 존재로 툴바 1개를 확인.
    expect(screen.getAllByRole('button', { name: '⊞ 표' })).toHaveLength(1);
    // <article>은 암묵적 role="article" — class 대신 role로 개수 확인.
    expect(screen.getAllByRole('article')).toHaveLength(1);
    expect(typeof controlRef.current.save).toBe('function');
    expect(typeof controlRef.current.isDirty).toBe('function');
  });

  it('apiBase 로 정본 img src 를 표시경로로 매핑해 마운트', () => {
    render(<DocEditor html={IMG_CANON} apiBase="" />);
    expect(screen.getByAltText('i')).toHaveAttribute('src', '/api/media/k1');
  });

  it('unmount 시 컨트롤러 해제', () => {
    const controlRef = { current: null };
    const { unmount } = render(<DocEditor html={IMG_CANON} apiBase="" controlRef={controlRef} />);
    expect(screen.getByRole('button', { name: '⊞ 표' })).toBeInTheDocument();
    unmount();
    expect(controlRef.current).toBeNull();
  });
});

describe('DocReader 래퍼', () => {
  // jsdom canvas 부재 회피 위해 img(fixedHeight) 블록만 사용.
  it('StrictMode 이중 마운트에도 .juldoc-reader 하나 + apiBase 이미지 매핑', () => {
    const html = '<article data-juldoc="1"><img src="/media/p1" alt="p"></article>';
    render(
      <StrictMode><DocReader html={html} apiBase="https://api.hanjul.io" /></StrictMode>,
    );
    // getByAltText는 매치가 정확히 1개일 때만 통과 — 이중 마운트로 콘텐츠가
    // 중복 렌더됐다면 "multiple elements" 에러로 실패해 원래 의도(중복 없음)를 그대로 검증.
    expect(screen.getByAltText('p')).toHaveAttribute('src', 'https://api.hanjul.io/api/media/p1');
  });
});
