import { useEffect, useRef, useState } from 'react';
import { useParams } from 'react-router-dom';
import { DocEditor, DocReader } from '@hanjul/doc';

import { apiBase } from '../services/api/api_client';
import {
  getShareHtml,
  getShareMeta,
  saveShareHtml,
  shareExportDocxUrl,
  shareExportEpubUrl,
  uploadMedia,
} from '../services/api/docs';
import { T } from '../theme';

const CAP_BADGE = { edit: '편집 가능', export: '내보내기 가능', view: '읽기 전용' };

// 한줄독 공개 공유 (/doc/s/:token) — 공개 열람. EDIT면 편집 가능, EXPORT면 수출 버튼.
export function DocSharePage() {
  const { token } = useParams();
  const controlRef = useRef(null);
  const [meta, setMeta] = useState(null);
  const [html, setHtml] = useState(null);
  const [mode, setMode] = useState('read');
  const [notice, setNotice] = useState(null); // { title, body }
  const [status, setStatus] = useState('');

  useEffect(() => {
    let alive = true;
    setNotice(null);
    Promise.all([getShareMeta(token), getShareHtml(token)])
      .then(([m, body]) => {
        if (!alive) return;
        setMeta(m);
        setHtml(body);
        setMode(m.capability === 'edit' ? 'edit' : 'read');
      })
      .catch((err) => {
        if (!alive) return;
        if (err.status === 404) setNotice({ title: '링크를 찾을 수 없습니다', body: '회수되었거나 존재하지 않는 링크입니다.' });
        else setNotice({ title: '문제가 발생했습니다', body: '잠시 후 다시 시도해 주세요.' });
      });
    return () => { alive = false; };
  }, [token]);

  async function enterRead() {
    const ctrl = controlRef.current;
    if (ctrl && ctrl.isDirty()) {
      const ok = await ctrl.save();
      if (!ok) return;
    }
    try {
      const body = await getShareHtml(token);
      setHtml(body);
    } catch { /* 기존 html 유지 */ }
    setMode('read');
  }

  function enterEdit() {
    if (meta?.capability !== 'edit') return;
    setStatus('');
    setMode('edit');
  }

  function onStatus(state, err) {
    if (state === 'saving') setStatus('저장 중…');
    else if (state === 'saved') setStatus('저장됨');
    else if (state === 'error') setStatus(err?.status === 403 ? '편집 권한이 없어요.' : `저장 실패: ${err?.message || err}`);
  }

  if (notice) {
    return (
      <div style={{ maxWidth: 480, margin: '18vh auto 0', textAlign: 'center', padding: '0 24px' }}>
        <h2 style={{ color: T.textStrong, fontSize: 20, margin: '0 0 8px' }}>{notice.title}</h2>
        <p style={{ color: T.muted, fontSize: 14 }}>{notice.body}</p>
      </div>
    );
  }
  if (!meta) return <Center>불러오는 중…</Center>;

  const canEdit = meta.capability === 'edit';
  const canExport = meta.capability === 'export';

  return (
    <div style={{ maxWidth: 940, margin: '0 auto', padding: '28px 24px 80px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap', marginBottom: 18 }}>
        <h1 style={{ margin: 0, fontSize: 20, fontWeight: 800, color: T.ink, flex: 1, minWidth: 160 }}>{meta.title}</h1>
        <span style={{ padding: '3px 10px', background: T.tint, color: T.text, borderRadius: 999, fontSize: 11.5, fontWeight: 700 }}>
          {CAP_BADGE[meta.capability] || '읽기 전용'}
        </span>
        {canEdit && (
          <div style={{ display: 'inline-flex', border: `1px solid ${T.border}`, borderRadius: 10, overflow: 'hidden' }}>
            <button onClick={enterRead} aria-pressed={mode === 'read'} style={segBtn(mode === 'read')}>읽기</button>
            <button onClick={enterEdit} aria-pressed={mode === 'edit'} style={segBtn(mode === 'edit')}>편집</button>
          </div>
        )}
        {canExport && (
          <>
            <a href={shareExportEpubUrl(token)} download={`${meta.title || 'document'}.epub`} style={linkBtn}>EPUB</a>
            <a href={shareExportDocxUrl(token)} download={`${meta.title || 'document'}.docx`} style={linkBtn}>DOCX</a>
          </>
        )}
        {status && <span style={{ fontSize: 13, color: T.muted }}>{status}</span>}
      </div>

      {mode === 'edit' && canEdit ? (
        <DocEditor
          html={html}
          apiBase={apiBase}
          controlRef={controlRef}
          onSave={(outer) => saveShareHtml(token, outer)}
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
const linkBtn = { padding: '9px 14px', borderRadius: 10, border: `1px solid ${T.border}`, background: T.surface, color: T.textMid, fontSize: 13, fontWeight: 700, textDecoration: 'none', cursor: 'pointer' };
