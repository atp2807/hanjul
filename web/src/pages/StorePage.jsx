import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';

import { listStore } from '../services/api/books';
import { coverGradient, T } from '../theme';

function Cover({ url, title }) {
  if (url) {
    return (
      <img
        src={url}
        alt={title}
        loading="lazy"
        decoding="async"
        style={{ width: '100%', aspectRatio: '3/4.3', objectFit: 'cover', borderRadius: T.radius.lg }}
      />
    );
  }
  return (
    <div
      style={{
        width: '100%',
        aspectRatio: '3/4.3',
        borderRadius: T.radius.lg,
        background: coverGradient(title),
        display: 'flex',
        alignItems: 'flex-end',
        padding: 16,
        color: '#dff5ef',
        fontSize: 15,
        fontWeight: 700,
        lineHeight: 1.3,
        boxSizing: 'border-box',
      }}
    >
      {title}
    </div>
  );
}

const FEATURES = [
  ['📚 서점', '수천 권의 전자책과 취향 큐레이션으로 다음 책을 만나세요.'],
  ['✍️ 에디터', '집중을 위한 깨끗한 글쓰기 공간, 자동 저장으로 문장에만 몰입.'],
  ['🚀 출판', '표지와 가격을 정하면 클릭 몇 번으로 바로 서점에 출간.'],
];

export function StorePage() {
  const navigate = useNavigate();
  const [items, setItems] = useState([]);
  const [q, setQ] = useState('');
  const [query, setQuery] = useState('');
  const [kind, setKind] = useState(''); // '' | BOOK | WEBNOVEL
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    setLoading(true);
    listStore(query, kind || undefined)
      .then((d) => setItems(d.items))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [query, kind]);

  const TABS = [
    ['', '전체'],
    ['BOOK', '일반서적'],
    ['WEBNOVEL', '웹소설'],
  ];

  return (
    <div>
      {/* Hero */}
      <section style={{ padding: '8px 28px 28px', maxWidth: 1280, margin: '0 auto' }}>
        <div
          style={{
            borderRadius: T.radius.hero,
            background: `linear-gradient(140deg, ${T.heroFrom} 0%, ${T.heroTo} 100%)`,
            padding: '64px 52px 60px',
            position: 'relative',
            overflow: 'hidden',
          }}
        >
          <div style={{ position: 'absolute', right: -80, top: -80, width: 340, height: 340, borderRadius: 999, background: 'rgba(255,255,255,0.18)' }} />
          <div style={{ position: 'absolute', right: 140, bottom: -130, width: 260, height: 260, borderRadius: 999, background: 'rgba(255,255,255,0.12)' }} />
          <div style={{ position: 'relative', maxWidth: 660 }}>
            <div style={{ display: 'inline-flex', alignItems: 'center', gap: 8, padding: '7px 15px', background: 'rgba(255,255,255,0.45)', borderRadius: 999, fontSize: 13, fontWeight: 600, color: '#0a463b', marginBottom: 24 }}>
              읽고 · 쓰고 · 펴내다
            </div>
            <h1 style={{ margin: 0, fontSize: 'clamp(34px, 6vw, 58px)', lineHeight: 1.13, fontWeight: 800, letterSpacing: '-0.035em', color: '#06342c' }}>
              읽는 사람과<br />쓰는 사람이<br />만나는 곳
            </h1>
            <p style={{ margin: '22px 0 0', maxWidth: 500, fontSize: 18, lineHeight: 1.65, color: '#0d4339', fontWeight: 500 }}>
              서점·에디터·출판을 하나로 묶은 글쓰기 플랫폼. 당신의 문장이 책이 되는 가장 빠른 길.
            </p>
            <div style={{ display: 'flex', gap: 12, marginTop: 32, flexWrap: 'wrap' }}>
              <button
                onClick={() => navigate('/studio')}
                style={{ padding: '15px 30px', background: '#ffffff', color: '#0a463b', border: 'none', borderRadius: T.radius.lg, fontSize: 16, fontWeight: 700, cursor: 'pointer' }}
              >
                무료로 시작하기
              </button>
              <a
                href="#store-grid"
                style={{ padding: '15px 30px', background: 'rgba(255,255,255,0.25)', color: '#06342c', border: '1px solid rgba(255,255,255,0.6)', borderRadius: T.radius.lg, fontSize: 16, fontWeight: 600, textDecoration: 'none' }}
              >
                서점 둘러보기
              </a>
            </div>
          </div>
        </div>
      </section>

      {/* 서점 그리드 */}
      <section id="store-grid" style={{ padding: '20px 44px 24px', maxWidth: 1280, margin: '0 auto' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 22, flexWrap: 'wrap' }}>
          <h2 style={{ margin: 0, fontSize: 24, fontWeight: 800, color: T.ink, letterSpacing: '-0.025em' }}>이번 주 추천</h2>
          <form
            onSubmit={(e) => { e.preventDefault(); setQuery(q); }}
            style={{ marginLeft: 'auto', display: 'flex', gap: 8 }}
          >
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="제목 검색"
              style={{ padding: '9px 14px', border: `1px solid ${T.border}`, borderRadius: T.radius.md, width: 220, background: T.surface, fontFamily: 'inherit' }}
            />
            <button style={{ padding: '9px 16px', borderRadius: T.radius.md, border: 'none', background: T.ink, color: T.inkText, fontWeight: 600, cursor: 'pointer' }}>검색</button>
          </form>
        </div>

        <div style={{ display: 'flex', gap: 8, marginBottom: 22 }}>
          {TABS.map(([value, label]) => (
            <button
              key={value}
              onClick={() => setKind(value)}
              style={{
                padding: '7px 16px',
                borderRadius: T.radius.pill,
                border: `1px solid ${kind === value ? T.ink : T.border}`,
                background: kind === value ? T.ink : T.surface,
                color: kind === value ? T.inkText : T.textMid,
                fontWeight: 600,
                fontSize: 14,
                cursor: 'pointer',
              }}
            >
              {label}
            </button>
          ))}
        </div>

        {error && <p style={{ color: 'crimson' }}>불러오기 실패: {error}</p>}
        {loading && <p style={{ color: T.muted }}>불러오는 중…</p>}
        {!loading && items.length === 0 && <p style={{ color: T.muted }}>아직 출판된 책이 없어요.</p>}

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(170px, 1fr))', gap: 22 }}>
          {items.map((b) => (
            <Link key={b.id} to={`/books/${b.id}`} style={{ textDecoration: 'none', color: 'inherit' }}>
              <Cover url={b.coverUrl} title={b.title} />
              <div style={{ marginTop: 10, fontWeight: 700, fontSize: 15, color: T.textStrong }}>{b.title}</div>
              <div style={{ color: T.muted, fontSize: 13, marginTop: 2 }}>
                {b.priceAmt != null ? `${b.priceAmt.toLocaleString()}원` : '무료'}
              </div>
            </Link>
          ))}
        </div>
      </section>

      {/* Features */}
      <section style={{ padding: '24px 44px 80px', maxWidth: 1280, margin: '0 auto' }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 16 }}>
          {FEATURES.map(([title, desc]) => (
            <div key={title} style={{ background: T.surface, borderRadius: T.radius.xl, padding: '30px 26px' }}>
              <h3 style={{ margin: '0 0 9px', fontSize: 18, fontWeight: 700, color: T.ink }}>{title}</h3>
              <p style={{ margin: 0, fontSize: 14, lineHeight: 1.65, color: T.textSoft }}>{desc}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
