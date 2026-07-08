import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { useAuth } from '../auth/AuthContext';
import {
  createDocument,
  deleteDocument,
  listDocuments,
  uploadDocument,
} from '../services/api/docs';
import { T } from '../theme';

// 업로드 허용 포맷 (juldoc ingest 파서 대응).
const ACCEPT = '.md,.txt,.hwp,.hwpx,.docx,.pdf,.html,.htm,.csv,.pptx,.xlsx';
const PAGE_SIZE = 20;

// 한줄독 문서 목록 (/doc) — 목록·업로드·빈 문서 생성·삭제. 비로그인 동작, 로그인 시 내 문서 표시.
export function DocsPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const fileRef = useRef(null);
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [title, setTitle] = useState('');
  const [busy, setBusy] = useState(false);

  async function load(p = page) {
    setLoading(true);
    setError('');
    try {
      const data = await listDocuments({ page: p, pageSize: PAGE_SIZE });
      setItems(data.items);
      setTotal(data.total);
      setPage(data.page);
    } catch {
      setError('문서 목록을 불러오지 못했어요.');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load(1);
    // user 변동(로그인/로그아웃) 시 mine 반영 위해 재조회.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user]);

  async function handleUpload(e) {
    const file = e.target.files?.[0];
    e.target.value = '';
    if (!file) return;
    setBusy(true);
    setError('');
    try {
      const doc = await uploadDocument(file);
      navigate(`/doc/${doc.id}`);
    } catch (err) {
      setError(err.status === 413 ? '파일이 너무 커요.' : '업로드에 실패했어요.');
      setBusy(false);
    }
  }

  async function handleCreate(e) {
    e.preventDefault();
    setBusy(true);
    setError('');
    try {
      const doc = await createDocument(title.trim() || '제목 없음');
      navigate(`/doc/${doc.id}`);
    } catch {
      setError('문서를 만들지 못했어요.');
      setBusy(false);
    }
  }

  async function handleDelete(id, e) {
    e.stopPropagation();
    if (!window.confirm('이 문서를 삭제할까요?')) return;
    try {
      await deleteDocument(id);
      await load(page);
    } catch (err) {
      setError(err.status === 403 ? '소유자만 삭제할 수 있어요.' : '삭제에 실패했어요.');
    }
  }

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div style={{ maxWidth: 880, margin: '0 auto', padding: '40px 24px 80px' }}>
      <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', gap: 16, marginBottom: 6, flexWrap: 'wrap' }}>
        <div>
          <h1 style={{ margin: 0, fontSize: 26, fontWeight: 800, color: T.ink, letterSpacing: '-0.025em' }}>한줄독</h1>
          <p style={{ fontSize: 14, color: T.muted, margin: '6px 0 0' }}>
            PDF·DOCX·HWP·PPTX 를 웹으로 열고, 읽고, 공유하세요. 로그인 없이도 됩니다.
          </p>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button
            onClick={() => fileRef.current?.click()}
            disabled={busy}
            style={btnPrimary(busy)}
          >
            파일 업로드
          </button>
          <input ref={fileRef} type="file" accept={ACCEPT} hidden onChange={handleUpload} data-testid="doc-upload-input" />
        </div>
      </div>

      {/* 빈 문서 생성 */}
      <form onSubmit={handleCreate} style={{ display: 'flex', gap: 8, margin: '20px 0 22px' }}>
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="새 문서 제목 (비우면 '제목 없음')"
          aria-label="새 문서 제목"
          style={{ flex: 1, padding: '11px 13px', border: `1px solid ${T.border}`, borderRadius: 10, background: T.surface, fontFamily: 'inherit', fontSize: 14 }}
        />
        <button type="submit" disabled={busy} style={btnSecondary(busy)}>빈 문서 만들기</button>
      </form>

      {error && <div style={{ color: '#c63c23', fontSize: 13, marginBottom: 14 }}>{error}</div>}

      {/* 목록 */}
      <div style={{ background: T.surface, borderRadius: 18, padding: '8px 24px 12px', boxShadow: '0 1px 3px rgba(12,58,50,0.06)' }}>
        {loading && <p style={{ color: T.muted, padding: '20px 0', fontSize: 14 }}>불러오는 중…</p>}
        {!loading && items.length === 0 && (
          <p style={{ color: T.muted, padding: '24px 0', fontSize: 14 }}>아직 문서가 없어요. 위에서 업로드하거나 새로 만들어보세요.</p>
        )}
        {!loading && items.map((doc) => (
          <div
            key={doc.id}
            role="button"
            tabIndex={0}
            onClick={() => navigate(`/doc/${doc.id}`)}
            onKeyDown={(e) => { if (e.key === 'Enter') navigate(`/doc/${doc.id}`); }}
            style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '14px 0', borderBottom: `1px solid ${T.borderSoft}`, cursor: 'pointer' }}
          >
            <span style={{ flex: 1, fontSize: 15, fontWeight: 700, color: T.textStrong }}>{doc.title}</span>
            <span style={{ fontSize: 12, color: T.faint, textTransform: 'uppercase' }}>{doc.format}</span>
            {doc.mine && (
              <span style={{ padding: '3px 10px', background: '#e3f3ec', color: '#297961', borderRadius: 999, fontSize: 11.5, fontWeight: 700 }}>내 문서</span>
            )}
            <button
              onClick={(e) => handleDelete(doc.id, e)}
              aria-label={`${doc.title} 삭제`}
              style={{ padding: '6px 11px', borderRadius: 9, border: `1px solid ${T.border}`, background: T.surface, color: T.muted, fontSize: 12.5, cursor: 'pointer' }}
            >
              삭제
            </button>
          </div>
        ))}
      </div>

      {/* 페이지네이션 */}
      {totalPages > 1 && (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 14, marginTop: 18 }}>
          <button onClick={() => load(page - 1)} disabled={page <= 1} style={btnPage(page <= 1)}>이전</button>
          <span style={{ fontSize: 13, color: T.muted }}>{page} / {totalPages}</span>
          <button onClick={() => load(page + 1)} disabled={page >= totalPages} style={btnPage(page >= totalPages)}>다음</button>
        </div>
      )}
    </div>
  );
}

function btnPrimary(disabled) {
  return { padding: '11px 18px', borderRadius: 11, border: 'none', background: disabled ? T.faint : T.ink, color: T.inkText, fontSize: 14, fontWeight: 700, cursor: disabled ? 'default' : 'pointer', whiteSpace: 'nowrap' };
}
function btnSecondary(disabled) {
  return { padding: '11px 16px', borderRadius: 10, border: `1px solid ${T.border}`, background: T.surface, color: T.textMid, fontSize: 13.5, fontWeight: 700, cursor: disabled ? 'default' : 'pointer', whiteSpace: 'nowrap' };
}
function btnPage(disabled) {
  return { padding: '8px 16px', borderRadius: 9, border: `1px solid ${T.border}`, background: T.surface, color: disabled ? T.faint : T.textMid, fontSize: 13, fontWeight: 600, cursor: disabled ? 'default' : 'pointer' };
}
