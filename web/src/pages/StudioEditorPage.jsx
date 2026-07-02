import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';

import { getBookContent } from '../services/api/books';
import {
  distributeBook,
  downloadEpub,
  downloadOnix,
  uploadCover,
  getDistributions,
  getMyBooks,
  importText,
  publishBook,
  publishNow,
  deleteBook,
  schedulePublish,
  setBookPrice,
  setDiscount,
  suggestBlurb,
  setIsbn,
  submitBook,
  updateMeta,
} from '../services/api/studio';
import { STATUS_LABEL } from './StudioPage';
import { Icon } from '../components/Icon';
import { T } from '../theme';

const dlBtn = { display: 'inline-flex', alignItems: 'center', gap: 7 };

const CHANNELS = [
  ['KYOBO', '교보문고'],
  ['YES24', '예스24'],
  ['ALADIN', '알라딘'],
  ['RIDIBOOKS', '리디북스'],
];

const CATEGORIES = ['소설', '에세이', '시', '자기계발', '경제경영', '인문', '과학', '판타지', '로맨스', '기타'];

export function StudioEditorPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [book, setBook] = useState(null);
  const [text, setText] = useState('');
  const [price, setPrice] = useState('');
  const [discAmt, setDiscAmt] = useState('');
  const [discUntil, setDiscUntil] = useState('');
  const [isbn, setIsbnValue] = useState('');
  const [subtitle, setSubtitle] = useState('');
  const [description, setDescription] = useState('');
  const [category, setCategory] = useState('');
  const [coverUrl, setCoverUrl] = useState(null);
  const [coverBusy, setCoverBusy] = useState(false);
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
    if (summary) {
      setIsbnValue(summary.isbn || '');
      setSubtitle(summary.subtitle || '');
      setDescription(summary.description || '');
      setCategory(summary.category || '');
      setCoverUrl(summary.coverUrl || null);
    }
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
  async function doUpload(e) {
    const file = e.target.files?.[0];
    e.target.value = ''; // 같은 파일 재선택 허용
    if (!file) return;
    setCoverBusy(true);
    setError(null);
    try {
      const r = await uploadCover(id, file);
      setCoverUrl(r.coverUrl);
      notify('표지를 올렸어요.');
    } catch (err) {
      setError(err.status === 422 ? '이미지 파일(PNG·JPG·WebP, 5MB 이하)만 올릴 수 있어요.' : err.message);
    } finally {
      setCoverBusy(false);
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
  async function doDelete() {
    if (!window.confirm('이 책을 삭제할까요? 장·블록까지 모두 지워지고 되돌릴 수 없어요.')) return;
    try {
      await deleteBook(id);
      navigate('/studio');
    } catch (e) {
      setError(e.status === 409 ? '판매 이력이 있어 삭제할 수 없어요. 출판 취소만 가능해요.' : e.message);
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

  // 수익 미리보기 (SELF 70% · 개인 3.3% 원천징수)
  const pNum = parseInt(price || '0', 10) || 0;
  const gross = Math.round(pNum * 0.7);
  const wh = Math.round(gross * 0.033);
  const net = gross - wh;

  return (
    <div style={{ maxWidth: 820, margin: '0 auto', padding: '28px 24px' }}>
      <Link to="/studio" style={{ fontSize: 13, color: T.muted, textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: 3 }}><Icon name="chevron" size={13} stroke="currentColor" style={{ transform: 'rotate(180deg)' }} /> 스튜디오</Link>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, margin: '8px 0 4px' }}>
        <h2 style={{ margin: 0, fontWeight: 800, color: T.ink, letterSpacing: '-0.025em' }}>{book.title}</h2>
        <span style={{ padding: '4px 11px', background: published ? '#e3f3ec' : '#fff3da', color: published ? '#2f8a6f' : '#c79318', borderRadius: 999, fontSize: 12, fontWeight: 700 }}>
          {STATUS_LABEL[book.status] || book.status}
        </span>
      </div>
      <p style={{ color: T.muted, marginTop: 0, fontSize: 14 }}>
        블록 {blockCount}개{book.priceAmt != null ? ` · ${book.priceAmt.toLocaleString()}원` : ''}
      </p>
      {msg && <p style={{ color: '#2f8a6f' }}>{msg}</p>}
      {error && <p style={{ color: 'crimson' }}>{error}</p>}

      <Section title="책 정보">
        <input
          value={subtitle}
          onChange={(e) => setSubtitle(e.target.value)}
          placeholder="부제 (선택)"
          style={{ ...inp, width: '100%', boxSizing: 'border-box', marginBottom: 8 }}
        />
        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          rows={4}
          placeholder="책 소개 (스토어 상세에 노출)"
          style={{ width: '100%', boxSizing: 'border-box', padding: 12, border: '1px solid #ddd', borderRadius: 8, fontFamily: 'inherit', marginBottom: 8 }}
        />
        <button
          onClick={async () => {
            try {
              const { blurb } = await suggestBlurb(id);
              setDescription(blurb);
              notify('본문에서 소개문을 추천했어요. 다듬은 뒤 저장하세요.');
            } catch (e) {
              setError(e.message);
            }
          }}
          style={{ ...btn, marginLeft: 0, marginBottom: 8 }}
        >
          소개문 추천
        </button>
        <select value={category} onChange={(e) => setCategory(e.target.value)} style={inp}>
          <option value="">분류 선택</option>
          {CATEGORIES.map((c) => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>
        <button
          onClick={run(() => updateMeta(id, { subtitle, description, category }), '책 정보가 저장됐어요.')}
          style={btn}
        >
          정보 저장
        </button>
      </Section>

      <Section title="표지">
        <div style={{ display: 'flex', gap: 16, alignItems: 'flex-start' }}>
          <div style={{ width: 120, flexShrink: 0 }}>
            {coverUrl ? (
              <img src={coverUrl} alt="표지" style={{ width: '100%', aspectRatio: '3/4', objectFit: 'cover', borderRadius: 8, border: '1px solid #eee' }} />
            ) : (
              <div style={{ width: '100%', aspectRatio: '3/4', borderRadius: 8, background: '#f1f2f4', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#aaa', fontSize: 12 }}>
                표지 없음
              </div>
            )}
          </div>
          <div style={{ flex: 1 }}>
            <label style={{ ...primary, cursor: coverBusy ? 'default' : 'pointer', margin: 0, display: 'inline-flex', alignItems: 'center', gap: 6 }}>
              <Icon name="download" size={15} stroke="#fff" style={{ transform: 'rotate(180deg)' }} /> {coverBusy ? '올리는 중…' : '표지 이미지 올리기'}
              <input type="file" accept="image/png,image/jpeg,image/webp" onChange={doUpload} disabled={coverBusy} style={{ display: 'none' }} />
            </label>
            <div style={{ fontSize: 12, color: T.muted, marginTop: 8 }}>직접 만든 표지 이미지를 올려주세요. (PNG·JPG·WebP, 5MB 이하)</div>
          </div>
        </div>
      </Section>

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
        <button onClick={run(() => setBookPrice(id, parseInt(price || '0', 10)), '가격이 저장됐어요.')} style={btn}>가격 저장</button>
        <span style={{ color: T.faint, fontSize: 13, marginLeft: 8 }}>0이면 무료</span>
        {pNum > 0 && (
          <div style={{ marginTop: 16, background: T.ink, borderRadius: 14, padding: '18px 20px' }}>
            <div style={{ fontSize: 12, color: T.inkSoft, marginBottom: 12 }}>수익 미리보기 · SELF 1권 판매 기준 · 개인 작가</div>
            <div style={{ display: 'flex', gap: 18, flexWrap: 'wrap', color: '#fff', fontSize: 14 }}>
              <span style={{ color: T.inkSoft }}>판매가 <b style={{ color: '#fff' }}>{pNum.toLocaleString()}원</b></span>
              <span style={{ color: T.inkSoft }}>작가 몫(70%) <b style={{ color: '#fff' }}>{gross.toLocaleString()}원</b></span>
              <span style={{ color: T.inkSoft }}>원천징수(3.3%) <b style={{ color: '#ffb4a2' }}>−{wh.toLocaleString()}원</b></span>
              <span style={{ color: '#06342c', background: 'oklch(0.7 0.11 188)', padding: '2px 12px', borderRadius: 999, fontWeight: 800 }}>실지급 {net.toLocaleString()}원</span>
            </div>
            <div style={{ fontSize: 11.5, color: T.faint, marginTop: 10 }}>외부 서점 판매 시 작가 60% 기준 별도 정산.</div>
          </div>
        )}
      </Section>

      <Section title="기간 할인">
        <input type="number" value={discAmt} onChange={(e) => setDiscAmt(e.target.value)} placeholder="할인가" style={inp} /> 원
        <input type="datetime-local" value={discUntil} onChange={(e) => setDiscUntil(e.target.value)} style={{ ...inp, marginLeft: 8 }} /> 까지
        <button
          onClick={run(() => setDiscount(id, parseInt(discAmt || '0', 10), new Date(discUntil).toISOString()), '할인이 설정됐어요.')}
          style={btn}
        >
          할인 저장
        </button>
        <span style={{ color: '#aaa', fontSize: 13, marginLeft: 8 }}>종료시각까지 할인가로 판매</span>
      </Section>

      <Section title="ISBN">
        <input value={isbn} onChange={(e) => setIsbnValue(e.target.value)} placeholder="978-89-..." style={{ ...inp, width: 220 }} />
        <button onClick={run(() => setIsbn(id, isbn), 'ISBN이 저장됐어요.')} style={btn}>ISBN 저장</button>
        <span style={{ color: '#aaa', fontSize: 13, marginLeft: 8 }}>없으면 서점에 자체 식별자로 나갑니다</span>
      </Section>

      <Section title="파일 산출물">
        <button onClick={run(() => downloadEpub(id))} style={{ ...btn, ...dlBtn }}><Icon name="download" size={16} stroke={T.textMid} /> EPUB 내려받기</button>
        <button onClick={run(() => downloadOnix(id))} style={{ ...btn, ...dlBtn }}><Icon name="download" size={16} stroke={T.textMid} /> ONIX(메타) 내려받기</button>
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
        {published && <Link to={`/books/${id}`} style={{ color: '#111', display: 'inline-flex', alignItems: 'center', gap: 3 }}>스토어에서 보기 <Icon name="chevron" size={13} stroke="currentColor" /></Link>}
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

      <Section title="책 삭제">
        <button onClick={doDelete} style={{ ...btn, marginLeft: 0, color: '#c2410c', borderColor: '#f3cfc6' }}>이 책 삭제</button>
        <span style={{ color: '#aaa', fontSize: 13, marginLeft: 8 }}>되돌릴 수 없어요. 판매 이력이 있으면 출판 취소만 가능합니다.</span>
      </Section>
    </div>
  );
}

function labelOf(cd) {
  const found = CHANNELS.find(([v]) => v === cd);
  return found ? found[1] : cd;
}

const btn = { marginLeft: 8, padding: '9px 15px', borderRadius: 10, border: `1px solid ${T.border}`, background: T.surface, color: T.textMid, fontWeight: 600, cursor: 'pointer' };
const primary = { ...btn, background: T.ink, color: T.inkText, border: 'none' };
const inp = { padding: '10px 13px', border: `1px solid #dfeae5`, borderRadius: 11, width: 160, background: T.bg, fontFamily: 'inherit', color: T.textStrong };

function Section({ title, children }) {
  return (
    <section style={{ background: T.surface, borderRadius: 18, padding: 24, marginTop: 16 }}>
      <h3 style={{ fontSize: 15, fontWeight: 800, color: T.textStrong, margin: '0 0 14px' }}>{title}</h3>
      <div>{children}</div>
    </section>
  );
}

function Center({ children }) {
  return <p style={{ textAlign: 'center', color: T.muted, padding: 40 }}>{children}</p>;
}
