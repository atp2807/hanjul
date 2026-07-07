import { useEffect, useRef, useState } from 'react';
import { useParams } from 'react-router-dom';
import { DocEditor, DocReader } from '@hanjul/doc';

import { apiBase } from '../services/api/api_client';
import {
  createShare,
  exportDocx,
  exportEpub,
  getDocument,
  getDocumentHtml,
  listShares,
  revokeShare,
  saveDocumentHtml,
  uploadMedia,
} from '../services/api/docs';
import { T } from '../theme';

// 공유 링크는 서버 url(`/s/{token}`)이 아니라 hanjul 라우트(/doc/s/:token)로 만든다.
function shareLink(token) {
  const origin = typeof location !== 'undefined' ? location.origin : '';
  return `${origin}/doc/s/${token}`;
}

// 한줄독 단일 문서 (/doc/:id) — 읽기 기본, 편집 토글, EPUB/DOCX 수출, 공유링크 관리.
// ⚠️ 편집/공유 가시성: 백엔드 DocumentResponse 는 mine 만 노출하고 ownerless 여부는
//    감추므로(ownerless·타인소유 둘 다 mine=false), 클라는 편집·공유 토글을 낙관적으로
//    노출하고 실제 인가는 서버(ensure_can_modify)에 맡긴다 — 타인 소유면 저장 시 403 을
//    안내로 표시. ownerless(비로그인 생성) 문서의 편집을 유지하기 위한 선택.
export function DocPage() {
  const { id } = useParams();
  const controlRef = useRef(null);
  const [doc, setDoc] = useState(null);
  const [html, setHtml] = useState(null);
  const [mode, setMode] = useState('read');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [status, setStatus] = useState('');

  // 공유 패널
  const [sharePanel, setSharePanel] = useState(false);
  const [shares, setShares] = useState([]);
  const [shareCap, setShareCap] = useState('view');
  const [shareMsg, setShareMsg] = useState('');

  useEffect(() => {
    let alive = true;
    setLoading(true);
    setError('');
    Promise.all([getDocument(id), getDocumentHtml(id)])
      .then(([meta, body]) => {
        if (!alive) return;
        setDoc(meta);
        setHtml(body);
      })
      .catch(() => alive && setError('문서를 불러오지 못했어요.'))
      .finally(() => alive && setLoading(false));
    return () => { alive = false; };
  }, [id]);

  async function enterEdit() {
    // 편집 진입 전 최신 정본으로 마운트(서버 정화 반영).
    try {
      const body = await getDocumentHtml(id);
      setHtml(body);
    } catch { /* 기존 html 유지 */ }
    setStatus('');
    setMode('edit');
  }

  async function enterRead() {
    const ctrl = controlRef.current;
    if (ctrl && ctrl.isDirty()) {
      const ok = await ctrl.save();
      if (!ok) return; // 저장 실패 시 전환 중단(onStatus 가 이미 표시).
    }
    // 읽기 모드는 서버 정본만 조판 — 저장 후 재조회(정화 왕복 반영).
    try {
      const body = await getDocumentHtml(id);
      setHtml(body);
    } catch { /* 기존 html 유지 */ }
    setMode('read');
  }

  function onStatus(state, err) {
    if (state === 'saving') setStatus('저장 중…');
    else if (state === 'saved') setStatus('저장됨');
    else if (state === 'error') {
      setStatus(err?.status === 403 ? '소유자만 편집할 수 있어요.' : `저장 실패: ${err?.message || err}`);
    }
  }

  // EPUB/DOCX 수출 — <a href> 대신 인증 첨부 다운로드(apiClient.download, 결함: mine 문서 403).
  async function handleExport(kind) {
    setStatus('');
    try {
      if (kind === 'epub') await exportEpub(id, doc?.title);
      else await exportDocx(id, doc?.title);
    } catch (err) {
      setStatus(err?.status === 403 ? '소유자만 내보낼 수 있어요.' : `내보내기 실패: ${err?.message || err}`);
    }
  }

  // ── 공유 ────────────────────────────────────────────────
  async function loadShares() {
    try {
      const data = await listShares(id);
      setShares(data.items);
    } catch {
      setShareMsg('공유 링크를 불러오지 못했어요.');
    }
  }

  async function toggleSharePanel() {
    const next = !sharePanel;
    setSharePanel(next);
    if (next) {
      setShareMsg('');
      await loadShares();
    }
  }

  async function copyLink(url) {
    try {
      await navigator.clipboard.writeText(url);
      setShareMsg('링크를 복사했어요.');
    } catch {
      window.prompt('아래 링크를 복사하세요', url);
    }
  }

  async function issueShare() {
    setShareMsg('발급 중…');
    try {
      const link = await createShare(id, shareCap);
      await loadShares();
      await copyLink(shareLink(link.token));
    } catch (err) {
      setShareMsg(err.status === 403 ? '소유자만 공유할 수 있어요.' : '발급에 실패했어요.');
    }
  }

  async function handleRevoke(shareId) {
    try {
      await revokeShare(shareId);
      await loadShares();
    } catch {
      setShareMsg('회수에 실패했어요.');
    }
  }

  if (loading) return <Center>불러오는 중…</Center>;
  if (error) return <Center>{error}</Center>;

  return (
    <div style={{ maxWidth: 940, margin: '0 auto', padding: '28px 24px 80px' }}>
      {/* 헤더 / 컨트롤 */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap', marginBottom: 18 }}>
        <h1 style={{ margin: 0, fontSize: 20, fontWeight: 800, color: T.ink, flex: 1, minWidth: 160 }}>
          {doc?.title || '문서'}
        </h1>
        {doc?.mine && (
          <span style={{ padding: '3px 10px', background: '#e3f3ec', color: '#2f8a6f', borderRadius: 999, fontSize: 11.5, fontWeight: 700 }}>내 문서</span>
        )}
        <div style={{ display: 'inline-flex', border: `1px solid ${T.border}`, borderRadius: 10, overflow: 'hidden' }}>
          <button onClick={enterRead} aria-pressed={mode === 'read'} style={segBtn(mode === 'read')}>읽기</button>
          <button onClick={enterEdit} aria-pressed={mode === 'edit'} style={segBtn(mode === 'edit')}>편집</button>
        </div>
        <button onClick={toggleSharePanel} aria-pressed={sharePanel} style={ctrlBtn(sharePanel)}>공유</button>
        <button onClick={() => handleExport('epub')} style={linkBtn}>EPUB</button>
        <button onClick={() => handleExport('docx')} style={linkBtn}>DOCX</button>
        {status && <span style={{ fontSize: 13, color: T.muted }}>{status}</span>}
      </div>

      {/* 공유 패널 */}
      {sharePanel && (
        <div style={{ background: T.surface, border: `1px solid ${T.border}`, borderRadius: 14, padding: 18, marginBottom: 18 }}>
          <div style={{ fontSize: 14, fontWeight: 700, color: T.textStrong, marginBottom: 12 }}>공유 링크</div>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap', marginBottom: 12 }}>
            <select value={shareCap} onChange={(e) => setShareCap(e.target.value)} aria-label="공유 권한"
              style={{ padding: '9px 11px', border: `1px solid ${T.border}`, borderRadius: 9, background: T.surface, fontFamily: 'inherit', fontSize: 13.5 }}>
              <option value="view">읽기 전용 (VIEW)</option>
              <option value="edit">편집 가능 (EDIT)</option>
              <option value="export">내보내기 가능 (EXPORT)</option>
            </select>
            <button onClick={issueShare} style={btnPrimarySm}>링크 발급</button>
            {shareMsg && <span style={{ fontSize: 12.5, color: T.muted }}>{shareMsg}</span>}
          </div>
          {shares.length === 0 ? (
            <div style={{ fontSize: 13, color: T.muted }}>아직 발급된 링크가 없어요.</div>
          ) : (
            <ul style={{ listStyle: 'none', margin: 0, padding: 0, display: 'flex', flexDirection: 'column', gap: 6 }}>
              {shares.map((s) => {
                const url = shareLink(s.token);
                return (
                  <li key={s.id} style={{ display: 'flex', gap: 8, alignItems: 'center', fontSize: 13 }}>
                    <span style={{ fontWeight: 700, textTransform: 'uppercase', fontSize: 11, color: T.textMid, width: 56 }}>{s.capability}</span>
                    <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: T.muted, fontFamily: 'ui-monospace, Menlo, monospace', textDecoration: s.revoked ? 'line-through' : 'none' }}>{url}</span>
                    {s.revoked ? (
                      <span style={{ color: T.faint, fontSize: 12 }}>회수됨</span>
                    ) : (
                      <>
                        <button onClick={() => copyLink(url)} style={btnMini}>복사</button>
                        <button onClick={() => handleRevoke(s.id)} style={btnMini}>회수</button>
                      </>
                    )}
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      )}

      {/* 본문 */}
      {mode === 'edit' ? (
        <DocEditor
          html={html}
          apiBase={apiBase}
          controlRef={controlRef}
          onSave={(outer) => saveDocumentHtml(id, outer)}
          onUploadMedia={uploadMedia}
          onStatus={onStatus}
        />
      ) : (
        <DocReader html={html} apiBase={apiBase} />
      )}
    </div>
  );
}

function Center({ children }) {
  return <p style={{ textAlign: 'center', color: T.muted, padding: 54 }}>{children}</p>;
}
function segBtn(active) {
  return { padding: '9px 16px', border: 'none', background: active ? T.ink : T.surface, color: active ? T.inkText : T.textMid, fontSize: 13.5, fontWeight: 700, cursor: 'pointer' };
}
function ctrlBtn(active) {
  return { padding: '9px 15px', borderRadius: 10, border: `1px solid ${active ? T.ink : T.border}`, background: active ? T.ink : T.surface, color: active ? T.inkText : T.textMid, fontSize: 13.5, fontWeight: 700, cursor: 'pointer' };
}
const linkBtn = { padding: '9px 14px', borderRadius: 10, border: `1px solid ${T.border}`, background: T.surface, color: T.textMid, fontSize: 13, fontWeight: 700, textDecoration: 'none', cursor: 'pointer' };
const btnPrimarySm = { padding: '9px 15px', borderRadius: 9, border: 'none', background: T.ink, color: T.inkText, fontSize: 13.5, fontWeight: 700, cursor: 'pointer' };
const btnMini = { padding: '5px 10px', borderRadius: 8, border: `1px solid ${T.border}`, background: T.surface, color: T.textMid, fontSize: 12, cursor: 'pointer' };
