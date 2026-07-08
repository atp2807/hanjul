import { useEffect, useMemo, useRef, useState } from 'react';

import { Icon } from '../components/Icon';
import { useFocusTrap } from '../hooks/useFocusTrap';
import { paginateLines } from './paginateLines';
import { createPretextLineMeasurer } from './pretextLineMeasurer';
import { blockStyle, READER_STYLE, READER_THEMES } from './readerStyle';

const TAG_BY_TYPE = { P: 'p', H1: 'h1', H2: 'h2', H3: 'h3', QUOTE: 'blockquote' };

const SCALE_KEY = 'hanjul-reader-scale';
const THEME_KEY = 'hanjul-reader-theme';
const posKey = (bookId) => `hanjul-reader-pos-${bookId}`;

function readLS(key, fallback) {
  try {
    const v = localStorage.getItem(key);
    return v == null ? fallback : v;
  } catch {
    return fallback;
  }
}
function writeLS(key, value) {
  try {
    localStorage.setItem(key, String(value));
  } catch {
    /* ignore */
  }
}

// 한 페이지 분량의 블록 조각(fragment) 렌더. 텍스트는 React 노드로 넣어 자동 escape.
// 측정과 동일한 폰트/너비를 쓰므로 같은 줄로 다시 흐른다(측정==렌더).
function Fragment({ frag, scale, color }) {
  const st = blockStyle(frag.type);
  const marginBottom = `${st.marginBottom * scale}px`;

  if (frag.type === 'HR') return <hr style={{ marginBottom, borderColor: 'currentColor', opacity: 0.3 }} />;

  const Tag = TAG_BY_TYPE[frag.type] || 'p';
  return (
    <Tag
      style={{
        margin: 0,
        marginBottom,
        color,
        fontFamily: READER_STYLE.fontFamily,
        fontSize: `${st.fontPx * scale}px`,
        lineHeight: `${st.lineHeight * scale}px`,
        fontWeight: st.weight,
      }}
    >
      {frag.lines.join(' ')}
    </Tag>
  );
}

// H1 블록(장 제목 — flattenBlocks가 되살린 것)에서 목차 항목을 뽑는다. 태그 제거는 표시용.
function tocFromBlocks(blocks) {
  return (blocks || [])
    .filter((b) => b.type === 'H1')
    .map((b) => ({ id: b.id, label: b.html.replace(/<[^>]+>/g, '') }));
}

export function Reader({ blocks, bookId }) {
  const [tocOpen, setTocOpen] = useState(false);
  const tocPanelRef = useRef(null);
  // 목차 드롭다운 키보드 접근성 — 열릴 때 포커스 이동·Tab 트랩·Esc 닫기·포커스 리턴(lr-ca34f579 ②)
  useFocusTrap({ open: tocOpen, onClose: () => setTocOpen(false), containerRef: tocPanelRef });
  const [scale, setScale] = useState(() => parseFloat(readLS(SCALE_KEY, '1')) || 1);
  const [themeKey, setThemeKey] = useState(() =>
    READER_THEMES[readLS(THEME_KEY, 'light')] ? readLS(THEME_KEY, 'light') : 'light',
  );
  const [pageIdx, setPageIdx] = useState(() =>
    bookId ? parseInt(readLS(posKey(bookId), '0'), 10) || 0 : 0,
  );

  const theme = READER_THEMES[themeKey];

  // 설정·위치 영속 (이 기기)
  useEffect(() => writeLS(SCALE_KEY, scale), [scale]);
  useEffect(() => writeLS(THEME_KEY, themeKey), [themeKey]);

  const { page, fontFamily } = READER_STYLE;
  const contentWidth = page.width - page.padding * 2;
  const contentHeight = page.height - page.padding * 2;

  // 폰트 배율이 바뀌면 즉시 재조판 (줄 단위 재분할) — Pretext 강점.
  const pages = useMemo(() => {
    const measureLines = createPretextLineMeasurer({ contentWidth, scale });
    return paginateLines(blocks, { contentHeight, measureLines });
  }, [blocks, scale, contentWidth, contentHeight]);

  const idx = Math.min(pageIdx, Math.max(0, pages.length - 1));
  const currentFrags = pages[idx] || [];

  const toc = useMemo(() => tocFromBlocks(blocks), [blocks]);
  // 목차 항목(장 제목 블록)이 실제로 어느 페이지에 걸렸는지 — 조판 결과(pages)에서 첫 등장 페이지를 찾는다.
  const pageForBlock = useMemo(() => {
    const map = new Map();
    pages.forEach((frags, pageNo) => {
      for (const f of frags) if (!map.has(f.blockId)) map.set(f.blockId, pageNo);
    });
    return map;
  }, [pages]);

  function goPage(next) {
    setPageIdx(next);
    if (bookId) writeLS(posKey(bookId), next); // 읽던 위치 이어보기
  }

  function jumpToChapter(blockId) {
    const p = pageForBlock.get(blockId);
    if (p != null) goPage(p);
    setTocOpen(false);
  }

  const btn = { padding: '4px 10px', borderRadius: 6, border: `1px solid ${theme.fg}33`, background: 'transparent', color: theme.fg, cursor: 'pointer' };

  return (
    <div style={{ fontFamily, color: theme.fg }}>
      <div style={{ display: 'flex', gap: 8, marginBottom: 12, alignItems: 'center', flexWrap: 'wrap' }}>
        {toc.length > 0 && (
          <span style={{ position: 'relative' }}>
            <button
              style={btn}
              data-testid="toc-toggle"
              aria-expanded={tocOpen}
              onClick={() => setTocOpen((v) => !v)}
            >
              목차
            </button>
            {tocOpen && (
              <ul
                ref={tocPanelRef}
                role="menu"
                aria-label="목차"
                data-testid="toc-list"
                style={{
                  position: 'absolute', top: '100%', left: 0, marginTop: 4, zIndex: 10,
                  listStyle: 'none', padding: 6, minWidth: 180, maxHeight: 260, overflowY: 'auto',
                  background: theme.bg, border: `1px solid ${theme.fg}33`, borderRadius: 8,
                }}
              >
                {toc.map((t) => (
                  <li key={t.id}>
                    <button
                      onClick={() => jumpToChapter(t.id)}
                      style={{
                        display: 'block', width: '100%', textAlign: 'left', padding: '6px 8px',
                        border: 'none', background: 'transparent', color: theme.fg, cursor: 'pointer', fontSize: 14,
                      }}
                    >
                      {t.label}
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </span>
        )}
        <button style={btn} aria-label="글자 작게" onClick={() => setScale((s) => Math.max(0.7, +(s - 0.1).toFixed(2)))}>A-</button>
        <button style={btn} aria-label="글자 크게" onClick={() => setScale((s) => Math.min(2, +(s + 0.1).toFixed(2)))}>A+</button>
        <span style={{ fontSize: 13, opacity: 0.7 }}>배율 {scale.toFixed(1)}x</span>
        <span data-testid="reader-themes" style={{ display: 'flex', gap: 6, marginLeft: 12 }}>
          {Object.entries(READER_THEMES).map(([key, t]) => (
            <button
              key={key}
              data-testid={`theme-${key}`}
              aria-pressed={themeKey === key}
              aria-label={`${t.label} 테마`}
              onClick={() => setThemeKey(key)}
              title={t.label}
              style={{
                width: 22, height: 22, borderRadius: '50%', cursor: 'pointer',
                background: t.bg, border: themeKey === key ? '2px solid #2563eb' : `1px solid ${t.fg}55`,
              }}
            />
          ))}
        </span>
        <span style={{ marginLeft: 'auto', fontSize: 13, opacity: 0.7 }}>
          {pages.length ? idx + 1 : 0} / {pages.length}
        </span>
      </div>

      <div
        style={{
          width: page.width,
          maxWidth: '100%',
          height: page.height,
          padding: page.padding,
          boxSizing: 'border-box',
          border: `1px solid ${theme.fg}22`,
          borderRadius: 8,
          overflow: 'hidden',
          background: theme.bg,
          transition: 'background 0.2s, color 0.2s',
        }}
      >
        {currentFrags.map((frag, i) => (
          <Fragment key={`${frag.blockId}#${i}`} frag={frag} scale={scale} color={theme.fg} />
        ))}
      </div>

      <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
        <button style={{ ...btn, display: 'inline-flex', alignItems: 'center', gap: 4 }} disabled={idx <= 0} onClick={() => goPage(idx - 1)}>
          <Icon name="chevron" size={14} stroke="currentColor" style={{ transform: 'rotate(180deg)' }} /> 이전
        </button>
        <button style={{ ...btn, display: 'inline-flex', alignItems: 'center', gap: 4 }} disabled={idx >= pages.length - 1} onClick={() => goPage(idx + 1)}>
          다음 <Icon name="chevron" size={14} stroke="currentColor" />
        </button>
      </div>
    </div>
  );
}
