import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import { getBookContent } from '../services/api/books';
import {
  distributeBook,
  downloadEpub,
  downloadOnix,
  getDistributions,
  getMyBooks,
  importText,
  publishBook,
  publishNow,
  schedulePublish,
  setBookPrice,
  setIsbn,
  submitBook,
} from '../services/api/studio';
import { STATUS_LABEL } from './StudioPage';

const CHANNELS = [
  ['KYOBO', '교보문고'],
  ['YES24', '예스24'],
  ['ALADIN', '알라딘'],
  ['RIDIBOOKS', '리디북스'],
];

export function StudioEditorPage() {
  const { id } = useParams();
  const [book, setBook] = useState(null);
  const [text, setText] = useState('');
  const [price, setPrice] = useState('');
  const [isbn, setIsbnValue] = useState('');
  const [scheduleAt, setScheduleAt] = useState('');
  const [channel, setChannel] = useState('KYOBO');
  const [dists, setDists] = useState([]);
  const [msg, setMsg] = useState(null);
  const [error, setError] = useState(null);

  async function load() {
    const c = await getBookContent(id);
    setBook(c);
    setPrice(c.priceAmt != null ? String(c.priceAmt) : '');
    // ISBN·배포이력은 content 응답 밖이라 별도 조회
    const mine = await getMyBooks();
    const summary = mine.items.find((b) => b.id === id);
    if (summary) setIsbnValue(summary.isbn || '');
    if (c.status === 'PUBLISHED') {
      setDists(await getDistributions(id));
    }
  }
  useEffect(() => {
    load().catch((e) => setError(e.message));
  }, [id]);

  function notify(m) {
    setMsg(m);
    setError(null);
  }
  function run(fn, ok) {
    return async () => {
      try {
        await fn();
        if (ok) notify(ok);
        await load();
      } catch (e) {
        setError(e.message);
      }
    };
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
  async function doSchedule() {
    if (!scheduleAt) return setError('발행 시각을 선택하세요.');
    try {
      await schedulePublish(id, new Date(scheduleAt).toISOString());
      notify(`${new Date(scheduleAt).toLocaleString()}에 자동 발행 예약됐어요.`);
      await load();
    } catch (e) {
      setError(e.message);
    }
  }
  async function doDistribute() {
    try {
      const r = await distributeBook(id, channel);
      notify(
        r.statusCd === 'SENT'
          ? `${labelOf(channel)}로 배포 전송 완료.`
          : `배포 실패: ${r.message || ''}`,
      );
      await load();
    } catch (e) {
      setError(e.message);
    }
  }

  if (error && !book) return <Center>{error}</Center>;
  if (!book) return <Center>불러오는 중…</Center>;
  const blockCount = book.chapters.reduce((n, ch) => n + ch.blocks.length, 0);
  const published = book.status === 'PUBLISHED';

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
        <input type="number" value={price} onChange={(e) => setPrice(e.target.value)} style={inp} /> 원
        <button onClick={run(() => setBookPrice(id, parseInt(price || '0', 10)), '가격이 저장됐어요.')} style={btn}>저장</button>
        <span style={{ color: '#aaa', fontSize: 13, marginLeft: 8 }}>0이면 무료</span>
      </Section>

      <Section title="ISBN">
        <input value={isbn} onChange={(e) => setIsbnValue(e.target.value)} placeholder="978-89-..." style={{ ...inp, width: 220 }} />
        <button onClick={run(() => setIsbn(id, isbn), 'ISBN이 저장됐어요.')} style={btn}>저장</button>
        <span style={{ color: '#aaa', fontSize: 13, marginLeft: 8 }}>없으면 서점에 자체 식별자로 나갑니다</span>
      </Section>

      <Section title="파일 산출물">
        <button onClick={run(() => downloadEpub(id))} style={btn}>EPUB 내려받기</button>
        <button onClick={run(() => downloadOnix(id))} style={btn}>ONIX(메타) 내려받기</button>
      </Section>

      <Section title="출판">
        {book.status === 'DRAFT' && (
          <button onClick={run(submitBook.bind(null, id), '심사 제출됐어요.')} style={btn}>심사 제출</button>
        )}
        {book.status === 'REVIEW' && (
          <button onClick={run(publishBook.bind(null, id), '출판 완료! 스토어에 노출됩니다.')} style={primary}>출판</button>
        )}
        {!published && (
          <>
            <button onClick={run(publishNow.bind(null, id), '즉시 출간됐어요! 스토어에 노출됩니다.')} style={primary}>즉시 출간</button>
            <span style={{ display: 'block', marginTop: 12 }} />
            <input type="datetime-local" value={scheduleAt} onChange={(e) => setScheduleAt(e.target.value)} style={inp} />
            <button onClick={doSchedule} style={btn}>예약 발행</button>
            <span style={{ color: '#aaa', fontSize: 13, marginLeft: 8 }}>지정 시각에 자동 게시</span>
          </>
        )}
        {published && <Link to={`/books/${id}`} style={{ color: '#111' }}>스토어에서 보기 →</Link>}
      </Section>

      {published && (
        <Section title="서점 배포">
          <select value={channel} onChange={(e) => setChannel(e.target.value)} style={inp}>
            {CHANNELS.map(([v, l]) => (
              <option key={v} value={v}>{l}</option>
            ))}
          </select>
          <button onClick={doDistribute} style={primary}>배포 전송</button>
          {dists.length > 0 && (
            <ul style={{ listStyle: 'none', padding: 0, marginTop: 14, fontSize: 14 }}>
              {dists.map((d) => (
                <li key={d.id} style={{ padding: '6px 0', borderTop: '1px solid #f0f0f0' }}>
                  <b>{labelOf(d.channelCd)}</b>{' '}
                  <span style={{ color: d.statusCd === 'SENT' ? 'green' : 'crimson' }}>
                    {d.statusCd === 'SENT' ? '전송됨' : '실패'}
                  </span>{' '}
                  <span style={{ color: '#aaa' }}>{new Date(d.createdAt).toLocaleString()}</span>
                  {d.message && <span style={{ color: '#c00', marginLeft: 6 }}>{d.message}</span>}
                </li>
              ))}
            </ul>
          )}
        </Section>
      )}
    </div>
  );
}

function labelOf(cd) {
  const found = CHANNELS.find(([v]) => v === cd);
  return found ? found[1] : cd;
}

const btn = { marginLeft: 8, padding: '8px 14px', borderRadius: 8, border: '1px solid #ddd', background: '#fff', fontWeight: 600 };
const primary = { ...btn, background: '#111', color: '#fff', border: 'none' };
const inp = { padding: '8px 12px', border: '1px solid #ddd', borderRadius: 8, width: 160 };

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
