// reader 조판/렌더 테스트 (jsdom) — 정본 HTML → 실제 <div> 페이지.
// jsdom 엔 canvas measureText 가 없으므로, 텍스트 측정(Pretext) 경로를 타지 않는
// 블록(UL=perItem, IMG=fixedHeight)만 써서 조판을 검증한다 (측정 정합은 measure/paginate 테스트가 커버).
import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { mountReader } from './reader.js';

const CANON = '<article data-juldoc="1"><ul><li>항목 하나</li><li>항목 둘</li></ul></article>';

let el;
beforeEach(() => {
  el = document.createElement('div');
  document.body.appendChild(el);
});
afterEach(() => {
  el.remove();
});

describe('mountReader', () => {
  it('정본 HTML 을 페이지(.juldoc-page)로 조판', () => {
    const ctrl = mountReader(el, { html: CANON });
    expect(ctrl.pageCount).toBeGreaterThanOrEqual(1);
    expect(el.classList.contains('juldoc-reader')).toBe(true);
    expect(el.querySelectorAll('.juldoc-page').length).toBe(ctrl.pageCount);
    expect(el.textContent).toContain('항목 하나');
  });

  it('destroy 는 마운트를 비우고 클래스를 제거(멱등)', () => {
    const ctrl = mountReader(el, { html: CANON });
    ctrl.destroy();
    expect(el.innerHTML).toBe('');
    expect(el.classList.contains('juldoc-reader')).toBe(false);
    expect(() => ctrl.destroy()).not.toThrow(); // 멱등
  });

  it('apiBase 로 이미지 정본 src 를 표시 절대경로로 매핑해 렌더', () => {
    const html = '<article data-juldoc="1"><img src="/media/pic1" alt="p"></article>';
    mountReader(el, { html, apiBase: 'https://api.hanjul.io' });
    const img = el.querySelector('img');
    expect(img).not.toBeNull();
    expect(img.getAttribute('src')).toBe('https://api.hanjul.io/api/media/pic1');
  });

  it('apiBase 미지정이면 img src passthrough (정본 그대로)', () => {
    const html = '<article data-juldoc="1"><img src="/media/pic1" alt="p"></article>';
    mountReader(el, { html });
    expect(el.querySelector('img').getAttribute('src')).toBe('/media/pic1');
  });
});
