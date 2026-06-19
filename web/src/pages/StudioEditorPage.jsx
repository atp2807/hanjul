import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import { getBookContent } from '../services/api/books';
import { importText, publishBook, setBookPrice, submitBook } from '../services/api/studio';
import { STATUS_LABEL } from './StudioPage';

export function StudioEditorPage() {
  const { id } = useParams();
  const [book, setBook] = useState(null);
  const [text, setText] = useState('');
  const [price, setPrice] = useState('');
  const [msg, setMsg] = useState(null);
  const [error, setError] = useState(null);

  async function load() {
    const c = await getBookContent(id);
    setBook(c);
    setPrice(c.priceAmt != null ? String(c.priceAmt) : '');
  }
  useEffect(() => {
    load().catch((e) => setError(e.message));
  }, [id]);

  function notify(m) {
    setMsg(m);
    setError(null);
  }

  async function doImport() {
    if (!text.trim()) return;
    try {
      const r = await importText(id, text);
      notify(`${r.blockCount}개 블록이 새 장으로 추가됐어요.`);
      setText('');
      await load();
    } catch (e) {
      setError(e.message);
    }
  }
  async function doPrice() {
    try {
      await setBookPrice(id, parseInt(price || '0', 10));
      notify('가격이 저장됐어요.');
      await load();
    } catch (e) {
      setError(e.message);
    }
  }
  async function doSubmit() {
    try {
      await submitBook(id);
      notify('심사 제출됐어요.');
      await load();
    } catch (e) {
      setError(e.message);
    }
  }
  async function doPublish() {
    try {
      await publishBook(id);
      notify('출판 완료! 스토어에 노출됩니다.');
      await load();
    } catch (e) {
      setError(`출판 실패: ${e.message} (가격 설정 + 심사 제출이 먼저예요)`);
    }
  }

  if (error && !book) return <Center>{error}</Center>;
  if (!book) return <Center>불러오는 중…</Center>;
  const blockCount = book.chapters.reduce((n, ch) => n + ch.blocks.length, 0);

  return (
    <div style={{ maxWidth: 760, margin: '0 auto', padding: '28px 24px' }}>
      <Link to="/studio" style={{ fontSize: 13, color: '#888', textDecoration: 'none' }}>
        ← 스튜디오
      </Link>
      <h2 style={{ margin: '8px 0 4px', fontWeight: 700 }}>{book.title}</h2>
      <p style={{ color: '#888', marginTop: 0 }}>
        상태: <b>{STATUS_LABEL[book.status] || book.status}</b> · 블록 {blockCount}개
        {book.priceAmt != null ? ` · ${book.priceAmt.toLocaleString()}원` : ''}
      </p>
      {msg && <p style={{ color: 'green' }}>{msg}</p>}
      {error && <p style={{ color: 'crimson' }}>{error}</p>}

      <Section title="원고 추가">
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={10}
          placeholder={'# 장 제목\n\n빈 줄로 문단을 구분하세요.\n> 인용\n---'}
          style={{ width: '100%', boxSizing: 'border-box', padding: 12, border: '1px solid #ddd', borderRadius: 8, fontFamily: 'inherit' }}
        />
        <button onClick={doImport} style={btn}>장 추가</button>
      </Section>

      <Section title="가격">
        <input type="number" value={price} onChange={(e) => setPrice(e.target.value)} style={{ padding: '8px 12px', border: '1px solid #ddd', borderRadius: 8, width: 140 }} /> 원
        <button onClick={doPrice} style={btn}>저장</button>
        <span style={{ color: '#aaa', fontSize: 13, marginLeft: 8 }}>0이면 무료</span>
      </Section>

      <Section title="출판">
        {book.status === 'DRAFT' && <button onClick={doSubmit} style={btn}>심사 제출</button>}
        {book.status === 'REVIEW' && <button onClick={doPublish} style={{ ...btn, background: '#111', color: '#fff', border: 'none' }}>출판</button>}
        {book.status === 'PUBLISHED' && (
          <Link to={`/books/${id}`} style={{ color: '#111' }}>스토어에서 보기 →</Link>
        )}
      </Section>
    </div>
  );
}

const btn = { marginLeft: 8, padding: '8px 14px', borderRadius: 8, border: '1px solid #ddd', background: '#fff', fontWeight: 600 };

function Section({ title, children }) {
  return (
    <section style={{ marginTop: 24, paddingTop: 16, borderTop: '1px solid #f0f0f0' }}>
      <h3 style={{ fontSize: 15, margin: '0 0 10px' }}>{title}</h3>
      <div>{children}</div>
    </section>
  );
}

function Center({ children }) {
  return <p style={{ textAlign: 'center', color: '#999', padding: 40 }}>{children}</p>;
}
