// 로컬우선 글쓰기 페이지 — 자동 목차 사이드바 + 에디터.
// 작가는 파일/챕터를 "관리"하지 않는다: 제목(# )만 쓰면 목차가 자동 생성·점프.
import { TextSelection } from 'prosemirror-state';
import { useCallback, useRef, useState } from 'react';
import { useParams } from 'react-router-dom';

import { setBookContent, publishNow } from '../services/api/studio';
import { splitIntoChapters } from '../writer/core/chapters';
import { docToOutline } from '../writer/core/outline';
import { charCount } from '../writer/core/wordcount';
import { pmToNeutral } from '../writer/editor/pm_doc';
import { WriterEditor } from '../writer/editor/WriterEditor';

export function WritePage() {
  const { id } = useParams();
  const [outline, setOutline] = useState([]);
  const [msg, setMsg] = useState(null);
  const [publishing, setPublishing] = useState(false);
  const viewRef = useRef(null);

  const handleChange = useCallback((doc) => setOutline(docToOutline(doc)), []);
  const handleReady = useCallback(({ view }) => {
    viewRef.current = view;
  }, []);

  async function publish() {
    const view = viewRef.current;
    if (!view) return;
    setPublishing(true);
    setMsg(null);
    try {
      // 에디터 정본 → 헤딩 기준 챕터 → 백엔드 교체 → 즉시 출간
      const neutral = pmToNeutral(view.state.doc);
      if (charCount(neutral) === 0) {
        // 빈 글로 출판하면 책 내용이 통째로 비워짐 → 차단(데이터 손실 방지)
        setMsg({ ok: false, text: '내용이 없어요. 글을 먼저 쓰세요.' });
        setPublishing(false);
        return;
      }
      const chapters = splitIntoChapters(neutral);
      await setBookContent(id, chapters);
      await publishNow(id);
      setMsg({ ok: true, text: '출판 완료! 스토어에 노출됩니다.' });
    } catch (e) {
      const text =
        e.status === 422 ? '가격을 먼저 정하세요 (스튜디오에서 설정).'
          : e.status === 403 ? '이 책의 작가만 출판할 수 있어요.'
            : e.status === 401 ? '로그인이 필요해요.'
              : `출판 실패: ${e.message}`;
      setMsg({ ok: false, text });
    } finally {
      setPublishing(false);
    }
  }

  function jump(pos) {
    const view = viewRef.current;
    if (!view) return;
    view.focus();
    const sel = TextSelection.near(view.state.doc.resolve(pos + 1));
    view.dispatch(view.state.tr.setSelection(sel).scrollIntoView());
  }

  return (
    <div style={{ display: 'flex', height: '100%' }}>
      {/* 목차 — 독립 스크롤 */}
      <aside
        style={{
          width: 240,
          flexShrink: 0,
          height: '100%',
          overflowY: 'auto',
          padding: '28px 16px',
          borderRight: '1px solid #f0f0f0',
          boxSizing: 'border-box',
        }}
      >
        <div style={{ fontSize: 12, color: '#9ca3af', marginBottom: 10 }}>목차 (자동)</div>
        {outline.length === 0 ? (
          <p style={{ fontSize: 13, color: '#cbd5e1', lineHeight: 1.6 }}>
            제목(<code>#&nbsp;</code> 입력)을 넣으면 목차가 자동으로 생겨요.
          </p>
        ) : (
          <ul data-testid="outline" style={{ listStyle: 'none', padding: 0, margin: 0 }}>
            {outline.map((h) => (
              <li key={h.id}>
                <button
                  onClick={() => jump(h.pos)}
                  style={{
                    width: '100%',
                    display: 'flex',
                    justifyContent: 'space-between',
                    gap: 8,
                    border: 'none',
                    background: 'none',
                    cursor: 'pointer',
                    textAlign: 'left',
                    padding: '5px 6px',
                    paddingLeft: 6 + (h.level - 1) * 12,
                    borderRadius: 6,
                    fontSize: 14,
                    color: '#333',
                  }}
                >
                  <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{h.text}</span>
                  <span style={{ color: '#cbd5e1', fontSize: 12, flexShrink: 0 }}>{h.charCount.toLocaleString()}자</span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </aside>
      {/* 에디터 — 독립 스크롤. 왼쪽 기준 정렬, 오른쪽은 빈 여백으로 늘어남 */}
      <main style={{ flex: 1, height: '100%', overflowY: 'auto', padding: '28px 32px' }}>
        <div style={{ maxWidth: 720 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
            <button
              onClick={publish}
              disabled={publishing}
              style={{ padding: '8px 16px', borderRadius: 8, border: 'none', background: '#111', color: '#fff', fontWeight: 600, cursor: 'pointer' }}
            >
              {publishing ? '출판 중…' : '출판'}
            </button>
            {msg && <span style={{ fontSize: 13, color: msg.ok ? 'green' : 'crimson' }}>{msg.text}</span>}
          </div>
          <WriterEditor docId={id} onReady={handleReady} onChange={handleChange} />
        </div>
      </main>
    </div>
  );
}
