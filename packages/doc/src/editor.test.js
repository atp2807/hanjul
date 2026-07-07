// editor 저장 흐름 테스트 (jsdom) — DOM 이 곧 문서, 저장 = article.outerHTML.
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { mountEditor, computeScaledSize, downscaleImage } from './editor.js';

const CANON = '<article data-juldoc="1"><h1>제목</h1><p>본문</p></article>';

let el;
beforeEach(() => {
  el = document.createElement('div');
  document.body.appendChild(el);
});
afterEach(() => {
  el.remove();
  vi.useRealTimers();
});

describe('mountEditor', () => {
  it('정본 article 을 contenteditable 로 마운트', () => {
    mountEditor(el, { html: CANON });
    const article = el.querySelector('article[data-juldoc]');
    expect(article).not.toBeNull();
    expect(article.getAttribute('contenteditable')).toBe('true');
  });

  it('입력 시 dirty 로 전환하고 onDirty(true) 통지', () => {
    const onDirty = vi.fn();
    const ctrl = mountEditor(el, { html: CANON, onDirty });
    const article = el.querySelector('article');
    article.dispatchEvent(new window.Event('input', { bubbles: true }));
    expect(ctrl.isDirty()).toBe(true);
    expect(onDirty).toHaveBeenCalledWith(true);
  });

  it('save() 는 래퍼 포함 outerHTML 을 onSave 로 넘기고 dirty 해제', async () => {
    const onSave = vi.fn().mockResolvedValue({ ok: true });
    const onDirty = vi.fn();
    const ctrl = mountEditor(el, { html: CANON, onSave, onDirty });
    const article = el.querySelector('article');
    article.appendChild(document.createTextNode(' 추가'));
    article.dispatchEvent(new window.Event('input', { bubbles: true }));

    await ctrl.save();

    expect(onSave).toHaveBeenCalledTimes(1);
    const saved = onSave.mock.calls[0][0];
    expect(saved).toContain('data-juldoc="1"'); // 래퍼 보존
    expect(saved).toContain('추가');
    expect(ctrl.isDirty()).toBe(false);
    expect(onDirty).toHaveBeenLastCalledWith(false);
  });

  it('저장은 DOM 을 교체하지 않는다 (커서 점프 방지) — 노드 동일성 유지', async () => {
    const ctrl = mountEditor(el, { html: CANON, onSave: vi.fn() });
    const article = el.querySelector('article');
    await ctrl.save();
    expect(el.querySelector('article')).toBe(article); // 같은 노드
  });

  it('자동저장: 입력 2초 후 save 호출 (디바운스)', async () => {
    vi.useFakeTimers();
    const onSave = vi.fn().mockResolvedValue(undefined);
    const ctrl = mountEditor(el, { html: CANON, onSave });
    const article = el.querySelector('article');
    article.dispatchEvent(new window.Event('input', { bubbles: true }));
    expect(onSave).not.toHaveBeenCalled();
    await vi.advanceTimersByTimeAsync(2000);
    expect(onSave).toHaveBeenCalledTimes(1);
    void ctrl;
  });

  it('저장 실패: dirty 유지 + onStatus("error") + save() false 반환', async () => {
    const boom = new Error('network down');
    const onSave = vi.fn().mockRejectedValue(boom);
    const onStatus = vi.fn();
    const ctrl = mountEditor(el, { html: CANON, onSave, onStatus });
    const article = el.querySelector('article');
    article.dispatchEvent(new window.Event('input', { bubbles: true }));

    const ok = await ctrl.save();

    expect(ok).toBe(false);
    expect(ctrl.isDirty()).toBe(true); // 실패 시 dirty 해제 금지
    expect(onStatus).toHaveBeenCalledWith('saving');
    expect(onStatus).toHaveBeenLastCalledWith('error', boom);
  });

  it('저장 성공: onStatus saving→saved + save() true 반환', async () => {
    const onStatus = vi.fn();
    const ctrl = mountEditor(el, { html: CANON, onSave: vi.fn().mockResolvedValue(1), onStatus });
    const ok = await ctrl.save();
    expect(ok).toBe(true);
    expect(onStatus.mock.calls.map((c) => c[0])).toEqual(['saving', 'saved']);
  });

  it('drop 은 paste 와 동일하게 정규화 경유 삽입 (b→strong, script 제거)', () => {
    const ctrl = mountEditor(el, { html: CANON });
    const article = el.querySelector('article');

    // 커서를 <p> 끝에 위치시킨다 (insertFragment 는 현재 선택 위치에 삽입).
    const p = article.querySelector('p');
    const range = document.createRange();
    range.selectNodeContents(p);
    range.collapse(false);
    const sel = window.getSelection();
    sel.removeAllRanges();
    sel.addRange(range);

    const evt = new window.Event('drop', { bubbles: true, cancelable: true });
    evt.dataTransfer = {
      getData: (type) =>
        type === 'text/html' ? '<b>굵은드롭</b><script>evil()</script>' : '굵은드롭',
    };
    article.dispatchEvent(evt);

    expect(evt.defaultPrevented).toBe(true); // 브라우저 기본 삽입(비정화) 차단
    expect(article.innerHTML).toContain('<strong>굵은드롭</strong>'); // b→strong 정규화
    expect(article.innerHTML).not.toContain('script');
    expect(ctrl.isDirty()).toBe(true);
  });
});

// ── 표 삽입/편집 ────────────────────────────────────────────────

/** article 내부 셀에 커서(선택)를 놓는다 — 표 조작 ops 는 현재 셀 기준. */
function selectCell(cell) {
  const range = document.createRange();
  range.selectNodeContents(cell);
  range.collapse(true);
  const sel = window.getSelection();
  sel.removeAllRanges();
  sel.addRange(range);
}

describe('표 삽입/편집', () => {
  it('insertTable(3,2) — 첫 행 thead, 나머지 tbody, outerHTML 에 thead/tbody 포함', () => {
    const ctrl = mountEditor(el, { html: CANON });
    const article = el.querySelector('article');
    ctrl.insertTable(3, 2);

    const out = article.outerHTML;
    expect(out).toContain('<thead>');
    expect(out).toContain('<tbody>');
    expect(article.querySelectorAll('thead tr').length).toBe(1);
    expect(article.querySelectorAll('thead th').length).toBe(2);
    expect(article.querySelectorAll('tbody tr').length).toBe(2); // 3행 - 헤더 1
    expect(article.querySelectorAll('tbody tr:first-child td').length).toBe(2);
    expect(ctrl.isDirty()).toBe(true);
  });

  it('툴바 "표" 버튼 — prompt(3x2) 로 표 삽입', () => {
    const promptSpy = vi.spyOn(window, 'prompt').mockReturnValue('3x2');
    const ctrl = mountEditor(el, { html: CANON });
    const article = el.querySelector('article');
    const tableBtn = el.querySelector('.juldoc-toolbar button[data-action="insertTable"]');
    expect(tableBtn).not.toBeNull();
    tableBtn.click();
    expect(promptSpy).toHaveBeenCalled();
    expect(article.querySelector('table')).not.toBeNull();
    expect(article.querySelectorAll('thead th').length).toBe(2);
    promptSpy.mockRestore();
    void ctrl;
  });

  it('addRow — 현재 셀 아래 같은 열 수의 행 추가', () => {
    const ctrl = mountEditor(el, { html: CANON });
    const article = el.querySelector('article');
    ctrl.insertTable(2, 3); // thead 1 + tbody 1
    selectCell(article.querySelector('tbody td'));
    ctrl.addRow();
    expect(article.querySelectorAll('tbody tr').length).toBe(2);
    expect(article.querySelectorAll('tbody tr:last-child td').length).toBe(3);
  });

  it('deleteRow — 현재 행 삭제(마지막 한 행은 남긴다)', () => {
    const ctrl = mountEditor(el, { html: CANON });
    const article = el.querySelector('article');
    ctrl.insertTable(3, 2); // 총 3행
    selectCell(article.querySelector('tbody tr td'));
    ctrl.deleteRow();
    expect(article.querySelectorAll('table tr').length).toBe(2);
  });

  it('addColumn/deleteColumn — 모든 행에 열 추가·삭제(헤더는 th, 본문은 td)', () => {
    const ctrl = mountEditor(el, { html: CANON });
    const article = el.querySelector('article');
    ctrl.insertTable(2, 2);
    selectCell(article.querySelector('tbody td'));
    ctrl.addColumn();
    expect(article.querySelectorAll('thead th').length).toBe(3);
    expect(article.querySelectorAll('tbody tr:first-child td').length).toBe(3);

    selectCell(article.querySelector('tbody td'));
    ctrl.deleteColumn();
    expect(article.querySelectorAll('thead th').length).toBe(2);
    expect(article.querySelectorAll('tbody tr:first-child td').length).toBe(2);
  });
});

// ── 이미지 삽입/업로드 ──────────────────────────────────────────

describe('이미지 삽입/업로드', () => {
  it('uploadAndInsertImage — 응답 display_url 을 img src 로 삽입(원본 url 아님)', async () => {
    const onUploadMedia = vi.fn().mockResolvedValue({
      url: '/media/orig',
      display_url: '/media/disp1600',
      thumb_url: '/media/thumb320',
      bytes: 1,
      content_type: 'image/webp',
      width: 1600,
      height: 900,
    });
    const ctrl = mountEditor(el, { html: CANON, onUploadMedia });
    const article = el.querySelector('article');
    const file = new File(['x'], 'pic.png', { type: 'image/png' });

    await ctrl.uploadAndInsertImage(file);

    expect(onUploadMedia).toHaveBeenCalledTimes(1);
    const img = article.querySelector('img');
    expect(img).not.toBeNull();
    expect(img.getAttribute('src')).toBe('/media/disp1600'); // display_url(본문용)
    expect(img.getAttribute('src')).not.toBe('/media/orig'); // 원본 아님
    expect(img.getAttribute('alt')).toBe('pic.png');
    expect(ctrl.isDirty()).toBe(true);
  });

  it('uploadAndInsertImage — display_url 없으면 url 로 폴백', async () => {
    const onUploadMedia = vi.fn().mockResolvedValue({ url: '/media/only' });
    const ctrl = mountEditor(el, { html: CANON, onUploadMedia });
    const article = el.querySelector('article');
    await ctrl.uploadAndInsertImage(new File(['x'], 'p.png', { type: 'image/png' }));
    expect(article.querySelector('img').getAttribute('src')).toBe('/media/only');
    void ctrl;
  });

  it('업로드 실패해도 에디터 안 깨짐 — onStatus("error") 통지, img 미삽입', async () => {
    const boom = new Error('upload failed');
    const onUploadMedia = vi.fn().mockRejectedValue(boom);
    const onStatus = vi.fn();
    const ctrl = mountEditor(el, { html: CANON, onUploadMedia, onStatus });
    const article = el.querySelector('article');

    await ctrl.uploadAndInsertImage(new File(['x'], 'p.png', { type: 'image/png' }));

    expect(article.querySelector('img')).toBeNull();
    expect(onStatus).toHaveBeenLastCalledWith('error', boom);
    void ctrl;
  });

  // 축소 단계를 결정적 passthrough(원본 그대로)로 — createObjectURL 미제공 시 downscaleImage 는 원본 반환.
  function withoutObjectURL(fn) {
    const orig = window.URL;
    window.URL = {};
    try {
      return fn();
    } finally {
      window.URL = orig;
    }
  }

  it('paste 로 붙은 이미지 파일 감지 → 업로드 경로 호출(텍스트 정규화 우회)', async () => {
    const onUploadMedia = vi.fn().mockResolvedValue({ display_url: '/media/x' });
    mountEditor(el, { html: CANON, onUploadMedia });
    const article = el.querySelector('article');
    const file = new File(['x'], 'clip.png', { type: 'image/png' });

    const evt = new window.Event('paste', { bubbles: true, cancelable: true });
    evt.clipboardData = { files: [file], getData: () => '' };
    withoutObjectURL(() => article.dispatchEvent(evt));

    expect(evt.defaultPrevented).toBe(true); // 텍스트 정규화 우회 확인
    await vi.waitFor(() => expect(onUploadMedia).toHaveBeenCalledWith(file));
  });

  it('drop 으로 떨어진 이미지 파일도 업로드 경로 호출', async () => {
    const onUploadMedia = vi.fn().mockResolvedValue({ display_url: '/media/y' });
    mountEditor(el, { html: CANON, onUploadMedia });
    const article = el.querySelector('article');
    const file = new File(['x'], 'drop.png', { type: 'image/png' });

    const evt = new window.Event('drop', { bubbles: true, cancelable: true });
    evt.dataTransfer = { files: [file], getData: () => '' };
    withoutObjectURL(() => article.dispatchEvent(evt));

    expect(evt.defaultPrevented).toBe(true);
    await vi.waitFor(() => expect(onUploadMedia).toHaveBeenCalledWith(file));
  });

  it('insertImage — javascript: src 는 삽입 거부(sanitizeUrl)', () => {
    const ctrl = mountEditor(el, { html: CANON });
    const article = el.querySelector('article');
    ctrl.insertImage('javascript:alert(1)', 'x');
    expect(article.querySelector('img')).toBeNull();
  });
});

// ── 클라 이미지 축소 (업로드 전) ────────────────────────────────

describe('computeScaledSize', () => {
  it('가로가 긴 이미지: 최대 변 4096 기준 비율 유지 축소', () => {
    expect(computeScaledSize(5000, 2500, 4096)).toEqual({ width: 4096, height: 2048, scaled: true });
  });
  it('세로가 긴 이미지도 최대 변 기준', () => {
    expect(computeScaledSize(2000, 8000, 4096)).toEqual({ width: 1024, height: 4096, scaled: true });
  });
  it('이미 작으면 그대로(scaled=false)', () => {
    expect(computeScaledSize(800, 600, 4096)).toEqual({ width: 800, height: 600, scaled: false });
  });
  it('정확히 4096 은 축소 안 함(초과만 축소)', () => {
    expect(computeScaledSize(4096, 4096, 4096).scaled).toBe(false);
  });
});

describe('downscaleImage (canvas mock)', () => {
  let origImage, origURL, createSpy;

  function stubImage(naturalWidth, naturalHeight) {
    class MockImage {
      set src(v) {
        this._src = v;
        Promise.resolve().then(() => this.onload && this.onload()); // 비동기 로드 시뮬
      }
      get src() { return this._src; }
      get naturalWidth() { return naturalWidth; }
      get naturalHeight() { return naturalHeight; }
    }
    window.Image = MockImage;
    window.URL = { createObjectURL: () => 'blob:mock', revokeObjectURL: () => {} };
  }

  beforeEach(() => {
    origImage = window.Image;
    origURL = window.URL;
  });
  afterEach(() => {
    window.Image = origImage;
    window.URL = origURL;
    createSpy?.mockRestore();
    createSpy = null;
  });

  it('4096px 초과 → canvas 로 4096 축소, webp File 로 반환', async () => {
    stubImage(5000, 2500);
    const canvas = {
      width: 0,
      height: 0,
      getContext: () => ({ drawImage: vi.fn() }),
      toBlob: (cb) => cb(new Blob(['webp-bytes'], { type: 'image/webp' })),
    };
    const realCreate = document.createElement.bind(document);
    createSpy = vi
      .spyOn(document, 'createElement')
      .mockImplementation((tag) => (tag === 'canvas' ? canvas : realCreate(tag)));

    const file = new File(['orig'], 'big.png', { type: 'image/png' });
    const out = await downscaleImage(file, document, 4096);

    expect(canvas.width).toBe(4096); // 치수 검증 — 최대 변 4096 으로 리사이즈
    expect(canvas.height).toBe(2048);
    expect(out).not.toBe(file); // 원본이 아니라 축소본
    expect(out.type).toBe('image/webp');
    expect(out.name).toBe('big.webp');
  });

  it('이미 작은 이미지는 원본 File 그대로(축소 안 함)', async () => {
    stubImage(800, 600);
    const file = new File(['x'], 'small.png', { type: 'image/png' });
    const out = await downscaleImage(file, document, 4096);
    expect(out).toBe(file);
  });

  it('환경 미지원(createObjectURL 없음) → 원본 그대로(서버가 최종 판단)', async () => {
    window.URL = {}; // createObjectURL 미제공
    const file = new File(['x'], 'x.png', { type: 'image/png' });
    const out = await downscaleImage(file, document, 4096);
    expect(out).toBe(file);
  });
});

// ── apiBase 미디어 매핑 (한줄 이식 신규) ────────────────────────
// 정본 `/media/{key}` ↔ 표시 `${apiBase}/api/media/{key}`. apiBase 미지정이면 passthrough.
describe('apiBase 미디어 매핑', () => {
  const IMG_CANON = '<article data-juldoc="1"><p>본문</p><img src="/media/abc" alt="사진"></article>';

  it('마운트 시 정본 img src 를 표시 절대경로로 매핑', () => {
    mountEditor(el, { html: IMG_CANON, apiBase: 'https://api.hanjul.io' });
    const img = el.querySelector('article img');
    expect(img.getAttribute('src')).toBe('https://api.hanjul.io/api/media/abc');
  });

  it('저장 직렬화 시 표시 src 를 정본 `/media/{key}` 로 되돌림 (라이브 DOM 은 표시 유지)', async () => {
    const onSave = vi.fn().mockResolvedValue(null);
    const ctrl = mountEditor(el, { html: IMG_CANON, apiBase: 'https://api.hanjul.io', onSave });
    await ctrl.save();
    const saved = onSave.mock.calls[0][0];
    expect(saved).toContain('src="/media/abc"'); // 정본 복원
    expect(saved).not.toContain('api.hanjul.io');
    // 라이브 DOM 은 표시 절대경로를 유지(저장 중 이미지 깨짐 방지).
    expect(el.querySelector('article img').getAttribute('src')).toBe('https://api.hanjul.io/api/media/abc');
  });

  it('빈 apiBase(dev, vite proxy) — `/media/X` ↔ `/api/media/X`', async () => {
    const onSave = vi.fn().mockResolvedValue(null);
    const ctrl = mountEditor(el, { html: IMG_CANON, apiBase: '', onSave });
    expect(el.querySelector('article img').getAttribute('src')).toBe('/api/media/abc');
    await ctrl.save();
    expect(onSave.mock.calls[0][0]).toContain('src="/media/abc"');
  });

  it('업로드 삽입 src 도 apiBase 로 표시 매핑', async () => {
    const onUploadMedia = vi.fn().mockResolvedValue({ display_url: '/media/up1' });
    const ctrl = mountEditor(el, { html: CANON, apiBase: 'https://api.hanjul.io', onUploadMedia });
    await ctrl.uploadAndInsertImage(new File(['x'], 'p.png', { type: 'image/png' }));
    expect(el.querySelector('article img').getAttribute('src')).toBe('https://api.hanjul.io/api/media/up1');
    void ctrl;
  });
});
