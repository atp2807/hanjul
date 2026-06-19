import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

import { listStore } from '../services/api/books';

function Cover({ url, title }) {
  if (url) {
    return (
      <img
        src={url}
        alt={title}
        loading="lazy"
        decoding="async"
        style={{ width: '100%', aspectRatio: '3/4', objectFit: 'cover', borderRadius: 8 }}
      />
    );
  }
  return (
    <div
      style={{
        width: '100%',
        aspectRatio: '3/4',
        borderRadius: 8,
        background: 'linear-gradient(135deg,#f3f4f6,#e5e7eb)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        color: '#9ca3af',
        fontSize: 13,
        padding: 12,
        textAlign: 'center',
        boxSizing: 'border-box',
      }}
    >
      {title}
    </div>
  );
}

export function StorePage() {
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
    <div style={{ maxWidth: 980, margin: '0 auto', padding: '28px 24px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 20 }}>
        <h2 style={{ margin: 0, fontWeight: 700 }}>스토어</h2>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            setQuery(q);
          }}
          style={{ marginLeft: 'auto', display: 'flex', gap: 8 }}
        >
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="제목 검색"
            style={{ padding: '8px 12px', border: '1px solid #ddd', borderRadius: 8, width: 220 }}
          />
          <button style={{ padding: '8px 14px', borderRadius: 8 }}>검색</button>
        </form>
      </div>

      <div style={{ display: 'flex', gap: 8, marginBottom: 18 }}>
        {TABS.map(([value, label]) => (
          <button
            key={value}
            onClick={() => setKind(value)}
            style={{
              padding: '6px 14px',
              borderRadius: 999,
              border: '1px solid #ddd',
              background: kind === value ? '#111' : '#fff',
              color: kind === value ? '#fff' : '#333',
              fontWeight: 600,
              fontSize: 14,
            }}
          >
            {label}
          </button>
        ))}
      </div>

      {error && <p style={{ color: 'crimson' }}>불러오기 실패: {error}</p>}
      {loading && <p style={{ color: '#999' }}>불러오는 중…</p>}
      {!loading && items.length === 0 && (
        <p style={{ color: '#999' }}>아직 출판된 책이 없어요.</p>
      )}

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))',
          gap: 20,
        }}
      >
        {items.map((b) => (
          <Link key={b.id} to={`/books/${b.id}`} style={{ textDecoration: 'none', color: 'inherit' }}>
            <Cover url={b.coverUrl} title={b.title} />
            <div style={{ marginTop: 8, fontWeight: 600, fontSize: 15 }}>{b.title}</div>
            <div style={{ color: '#666', fontSize: 13, marginTop: 2 }}>
              {b.priceAmt != null ? `${b.priceAmt.toLocaleString()}원` : '무료'}
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
