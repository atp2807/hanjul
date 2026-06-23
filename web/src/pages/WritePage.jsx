// 로컬우선 글쓰기 페이지 — 자동 목차 사이드바 + 에디터.
// 작가는 파일/챕터를 "관리"하지 않는다: 제목(# )만 쓰면 목차가 자동 생성·점프.
import { TextSelection } from 'prosemirror-state';
import { useCallback, useEffect, useRef, useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import { getMyBooks, setBookContent, publishNow } from '../services/api/studio';
import { docxToNeutral } from '../writer/adapters/docx_import';
import { splitIntoChapters } from '../writer/core/chapters';
import { docToOutline } from '../writer/core/outline';
import { charCount } from '../writer/core/wordcount';
import { neutralToPmDoc, pmToNeutral } from '../writer/editor/pm_doc';
import { WriterEditor } from '../writer/editor/WriterEditor';
import { listSnapshots, observeSnapshots, takeSnapshot } from '../writer/snapshots';

export function WritePage() {
  const { id } = useParams();
  const [outline, setOutline] = useState([]);
  const [snapshots, setSnapshots] = useState([]);
  const [totalChars, setTotalChars] = useState(0);
  const [goal, setGoalState] = useState(() => Number(localStorage.getItem(`hanjul-goal-${id}`)) || 0);
  const [msg, setMsg] = useState(null);
  const [publishing, setPublishing] = useState(false);
  const [focus, setFocus] = useState(false); // 집중 모드(방해 없는 쓰기)
  const [notes, setNotes] = useState(''); // 자료(인물·설정 메모)
  const [meta, setMeta] = useState(null); // 책 메타(표지·가격·소개·ISBN) — 출판 전 점검
  const viewRef = useRef(null);
  const ydocRef = useRef(null);
  const snapOffRef = useRef(null);
  const metaOffRef = useRef(null);

  const handleChange = useCallback((doc) => {
    setOutline(docToOutline(doc));
    setTotalChars(doc.textContent.length); // 진행도(글자수)
  }, []);

  function setGoal(n) {
    setGoalState(n);
    if (n > 0) localStorage.setItem(`hanjul-goal-${id}`, String(n));
    else localStorage.removeItem(`hanjul-goal-${id}`);
  }
  const handleReady = useCallback(({ view, ydoc }) => {
    viewRef.current = view;
    ydocRef.current = ydoc;
    snapOffRef.current?.(); // 이전 에디터 옵저버 해제
    setSnapshots(listSnapshots(ydoc));
    snapOffRef.current = observeSnapshots(ydoc, setSnapshots);

    // 자료 메모 (Y.Map LWW, 동기화·영속)
    metaOffRef.current?.();
    const wmeta = ydoc.getMap('writerMeta');
    setNotes(wmeta.get('notes') || '');
    const onMeta = () => setNotes(wmeta.get('notes') || '');
    wmeta.observe(onMeta);
    metaOffRef.current = () => wmeta.unobserve(onMeta);
  }, []);
  useEffect(() => () => { snapOffRef.current?.(); metaOffRef.current?.(); }, []);

  const refreshMeta = useCallback(() => {
    getMyBooks()
      .then((r) => setMeta(r?.items?.find((b) => b.id === id) || null)) // 응답 형태 변경에도 안전
      .catch(() => {}); // 미로그인/네트워크면 점검 숨김
  }, [id]);
  useEffect(() => { refreshMeta(); }, [refreshMeta]);

  function updateNotes(text) {
    setNotes(text);
    ydocRef.current?.getMap('writerMeta').set('notes', text);
  }

  function saveSnapshot() {
    const view = viewRef.current;
    const ydoc = ydocRef.current;
    if (!view || !ydoc) return;
    takeSnapshot(ydoc, pmToNeutral(view.state.doc), Date.now());
    setMsg({ ok: true, text: '되돌리기 지점을 저장했어요.' });
  }

  function restoreSnapshot(snap) {
    const view = viewRef.current;
    const ydoc = ydocRef.current;
    if (!view || !ydoc) return;
    if (!snap?.neutral?.blocks?.length) {
      setMsg({ ok: false, text: '복원할 내용이 없는 지점이에요.' });
      return;
    }
    try {
      // 복원 전 현재 상태도 지점으로 저장 → 잘못 눌러도 되돌릴 수 있음
      takeSnapshot(ydoc, pmToNeutral(view.state.doc), Date.now());
      replaceContent(snap.neutral);
      setMsg({ ok: true, text: '그 지점으로 되돌렸어요. (직전 상태도 지점으로 저장됨)' });
    } catch (e) {
      setMsg({ ok: false, text: `복원 실패: ${e?.message ?? String(e)}` });
    }
  }

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
      refreshMeta();
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

  function replaceContent(neutral) {
    const view = viewRef.current;
    if (!view || !neutral.blocks.length) return;
    const newDoc = neutralToPmDoc(neutral);
    view.dispatch(view.state.tr.replaceWith(0, view.state.doc.content.size, newDoc.content));
    view.focus();
  }

  async function importDocx(e) {
    const file = e.target.files?.[0];
    e.target.value = ''; // 같은 파일 재선택 허용
    if (!file) return;
    setMsg(null);
    try {
      const neutral = await docxToNeutral(await file.arrayBuffer());
      if (!neutral.blocks.length) {
        setMsg({ ok: false, text: '가져올 내용이 없어요.' });
        return;
      }
      replaceContent(neutral);
      setMsg({ ok: true, text: `DOCX ${neutral.blocks.length}개 블록을 가져왔어요.` });
    } catch (err) {
      setMsg({ ok: false, text: `가져오기 실패: ${err?.message ?? String(err)}` });
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
      {/* 목차 — 독립 스크롤. 집중 모드면 숨김 */}
      {!focus && (
      <aside
        data-testid="outline-aside"
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

        {snapshots.length > 0 && (
          <div style={{ marginTop: 22, paddingTop: 14, borderTop: '1px solid #f0f0f0' }}>
            <div style={{ fontSize: 12, color: '#9ca3af', marginBottom: 8 }}>되돌리기 지점</div>
            <ul data-testid="snapshots" style={{ listStyle: 'none', padding: 0, margin: 0 }}>
              {snapshots.map((s) => (
                <li key={s.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '4px 6px', fontSize: 13 }}>
                  <span style={{ color: '#666' }}>{new Date(s.ts).toLocaleTimeString()}</span>
                  <button
                    onClick={() => restoreSnapshot(s)}
                    style={{ border: '1px solid #ddd', background: '#fff', borderRadius: 6, padding: '2px 8px', fontSize: 12, cursor: 'pointer' }}
                  >
                    복원
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}

        <div style={{ marginTop: 22, paddingTop: 14, borderTop: '1px solid #f0f0f0' }}>
          <div style={{ fontSize: 12, color: '#9ca3af', marginBottom: 8 }}>자료 📎 (인물·설정 메모)</div>
          <textarea
            data-testid="notes"
            value={notes}
            onChange={(e) => updateNotes(e.target.value)}
            rows={8}
            placeholder="등장인물, 설정, 자료를 여기에…"
            style={{ width: '100%', boxSizing: 'border-box', padding: 10, border: '1px solid #ddd', borderRadius: 8, fontFamily: 'inherit', fontSize: 13, resize: 'vertical' }}
          />
        </div>
      </aside>
      )}
      {/* 에디터 — 독립 스크롤. 왼쪽 기준 정렬, 오른쪽은 빈 여백으로 늘어남 */}
      <main style={{ flex: 1, height: '100%', overflowY: 'auto', padding: '28px 32px' }}>
        <div style={{ maxWidth: 720 }}>
          {focus && (
            <button
              onClick={() => setFocus(false)}
              style={{ position: 'fixed', top: 12, right: 16, zIndex: 20, padding: '6px 12px', borderRadius: 8, border: '1px solid #ddd', background: '#fff', fontSize: 13, cursor: 'pointer' }}
            >
              집중 해제
            </button>
          )}
          {!focus && (
          <>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
            <button
              onClick={publish}
              disabled={publishing}
              style={{ padding: '8px 16px', borderRadius: 8, border: 'none', background: '#111', color: '#fff', fontWeight: 600, cursor: 'pointer' }}
            >
              {publishing ? '출판 중…' : '출판'}
            </button>
            <label style={{ padding: '8px 14px', borderRadius: 8, border: '1px solid #ddd', background: '#fff', fontWeight: 600, fontSize: 13, cursor: 'pointer' }}>
              가져오기(.docx)
              <input type="file" accept=".docx" onChange={importDocx} style={{ display: 'none' }} />
            </label>
            <button
              onClick={saveSnapshot}
              style={{ padding: '8px 14px', borderRadius: 8, border: '1px solid #ddd', background: '#fff', fontWeight: 600, fontSize: 13, cursor: 'pointer' }}
            >
              지점 저장
            </button>
            <button
              onClick={() => setFocus(true)}
              style={{ padding: '8px 14px', borderRadius: 8, border: '1px solid #ddd', background: '#fff', fontWeight: 600, fontSize: 13, cursor: 'pointer' }}
            >
              집중
            </button>
            {msg && <span style={{ fontSize: 13, color: msg.ok ? 'green' : 'crimson' }}>{msg.text}</span>}
          </div>

          {/* 목표/진행 — 동기부여 */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10, fontSize: 13, color: '#666' }}>
            <span>목표</span>
            <input
              type="number"
              min="0"
              data-testid="goal-input"
              value={goal || ''}
              onChange={(e) => setGoal(Math.max(0, Number(e.target.value) || 0))}
              placeholder="0"
              style={{ width: 80, padding: '4px 8px', border: '1px solid #ddd', borderRadius: 6 }}
            />
            <span>자</span>
            <span data-testid="progress" style={{ marginLeft: 6, color: goal && totalChars >= goal ? '#16a34a' : '#666' }}>
              {goal ? (totalChars >= goal ? `목표 달성 🎉 ${totalChars.toLocaleString()} / ${goal.toLocaleString()}자` : `${totalChars.toLocaleString()} / ${goal.toLocaleString()}자`) : `${totalChars.toLocaleString()}자`}
            </span>
            {goal > 0 && (
              <span style={{ flex: 1, height: 6, background: '#f0f0f0', borderRadius: 3, overflow: 'hidden', maxWidth: 180 }}>
                <span style={{ display: 'block', height: '100%', width: `${Math.min(100, (totalChars / goal) * 100)}%`, background: totalChars >= goal ? '#16a34a' : '#111' }} />
              </span>
            )}
          </div>

          {/* 출판 전 점검 — 누락 항목 안내(차단 아님) */}
          {meta && (
            <div data-testid="checklist" style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 10, marginBottom: 12, fontSize: 13 }}>
              {[
                { label: '내용', ok: totalChars > 0 },
                { label: '표지', ok: !!meta.coverUrl },
                { label: '가격', ok: meta.priceAmt != null },
                { label: '소개', ok: !!meta.description },
                { label: 'ISBN', ok: !!meta.isbn, optional: true },
              ].map((c) => (
                <span key={c.label} style={{ color: c.ok ? '#16a34a' : c.optional ? '#9ca3af' : '#d97706' }}>
                  {c.ok ? '✓' : '✗'} {c.label}
                  {c.optional && !c.ok ? '(선택)' : ''}
                </span>
              ))}
              <Link to={`/studio/${id}`} style={{ color: '#111', marginLeft: 4 }}>책 정보 설정 →</Link>
            </div>
          )}
          </>
          )}

          <WriterEditor docId={id} onReady={handleReady} onChange={handleChange} />
        </div>
      </main>
    </div>
  );
}
