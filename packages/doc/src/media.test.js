// media src 매핑 헬퍼 테스트 — 정본 `/media/{key}` ↔ 표시 `${apiBase}/api/media/{key}`.
import { describe, it, expect } from 'vitest';
import { mediaSrcToDisplay, mediaSrcToCanonical, mapImgSrcs } from './media.js';

describe('mediaSrcToDisplay', () => {
  it('apiBase 미지정(null/undefined) 이면 passthrough', () => {
    expect(mediaSrcToDisplay('/media/abc', undefined)).toBe('/media/abc');
    expect(mediaSrcToDisplay('/media/abc', null)).toBe('/media/abc');
  });

  it('빈 apiBase(dev, vite proxy): `/media/X` → `/api/media/X`', () => {
    expect(mediaSrcToDisplay('/media/abc', '')).toBe('/api/media/abc');
  });

  it('절대 apiBase(prod): `/media/X` → `${apiBase}/api/media/X`', () => {
    expect(mediaSrcToDisplay('/media/abc', 'https://api.hanjul.io')).toBe(
      'https://api.hanjul.io/api/media/abc',
    );
  });

  it('정본 경로가 아닌 src 는 손대지 않음 (http/data/앵커)', () => {
    expect(mediaSrcToDisplay('https://cdn.example/x.png', 'https://api.hanjul.io')).toBe(
      'https://cdn.example/x.png',
    );
    expect(mediaSrcToDisplay('data:image/png;base64,AAAA', '')).toBe('data:image/png;base64,AAAA');
  });
});

describe('mediaSrcToCanonical', () => {
  it('apiBase 미지정이면 passthrough', () => {
    expect(mediaSrcToCanonical('/api/media/abc', undefined)).toBe('/api/media/abc');
    expect(mediaSrcToCanonical('/media/abc', null)).toBe('/media/abc');
  });

  it('빈 apiBase: `/api/media/X` → `/media/X`', () => {
    expect(mediaSrcToCanonical('/api/media/abc', '')).toBe('/media/abc');
  });

  it('절대 apiBase: `${apiBase}/api/media/X` → `/media/X`', () => {
    expect(mediaSrcToCanonical('https://api.hanjul.io/api/media/abc', 'https://api.hanjul.io')).toBe(
      '/media/abc',
    );
  });

  it('절대 apiBase 라도 상대 표시경로(/api/media/…)면 정본으로 되돌림', () => {
    expect(mediaSrcToCanonical('/api/media/abc', 'https://api.hanjul.io')).toBe('/media/abc');
  });

  it('표시 경로가 아닌 src 는 손대지 않음', () => {
    expect(mediaSrcToCanonical('https://cdn.example/x.png', 'https://api.hanjul.io')).toBe(
      'https://cdn.example/x.png',
    );
  });

  it('display→canonical 왕복 항등 (prod)', () => {
    const base = 'https://api.hanjul.io';
    const disp = mediaSrcToDisplay('/media/k9', base);
    expect(mediaSrcToCanonical(disp, base)).toBe('/media/k9');
  });
});

describe('mapImgSrcs', () => {
  it('루트 하위 모든 img src 를 fn 으로 변환(제자리)', () => {
    const root = document.createElement('div');
    root.innerHTML = '<p>x</p><img src="/media/a"><img src="/media/b"><img>';
    mapImgSrcs(root, (s) => mediaSrcToDisplay(s, ''));
    const imgs = root.querySelectorAll('img');
    expect(imgs[0].getAttribute('src')).toBe('/api/media/a');
    expect(imgs[1].getAttribute('src')).toBe('/api/media/b');
    expect(imgs[2].getAttribute('src')).toBeNull(); // src 없는 img 는 건너뜀
  });
});
