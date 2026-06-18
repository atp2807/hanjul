import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import { getStoreDetail } from '../services/api/books';

export function BookDetailPage() {
  const { id } = useParams();
  const [book, setBook] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    getStoreDetail(id)
      .then(setBook)
      .catch((e) => setError(e.message));
  }, [id]);

  if (error) return <Center>불러오기 실패: {error}</Center>;
  if (!book) return <Center>불러오는 중…</Center>;

  return (
    <div style={{ maxWidth: 760, margin: '0 auto', padding: '32px 24px', display: 'flex', gap: 28 }}>
      <div style={{ width: 220, flexShrink: 0 }}>
        {book.coverUrl ? (
          <img src={book.coverUrl} alt={book.title} style={{ width: '100%', borderRadius: 10 }} />
        ) : (
          <div style={{ width: '100%', aspectRatio: '3/4', borderRadius: 10, background: '#f1f2f4' }} />
        )}
      </div>
      <div style={{ flex: 1 }}>
        <h1 style={{ margin: '0 0 6px', fontWeight: 700 }}>{book.title}</h1>
        {book.subtitle && <p style={{ color: '#666', marginTop: 0 }}>{book.subtitle}</p>}
        <p style={{ fontSize: 20, fontWeight: 700, margin: '16px 0' }}>
          {book.priceAmt != null ? `${book.priceAmt.toLocaleString()}원` : '무료'}
        </p>
        <div style={{ display: 'flex', gap: 10 }}>
          <Link
            to={`/read/${book.id}`}
            style={{
              padding: '10px 20px',
              background: '#111',
              color: '#fff',
              borderRadius: 8,
              textDecoration: 'none',
              fontWeight: 600,
            }}
          >
            읽기
          </Link>
          <button style={{ padding: '10px 20px', borderRadius: 8, border: '1px solid #ddd' }}>
            구매
          </button>
        </div>
        <p style={{ color: '#aaa', fontSize: 12, marginTop: 24 }}>
          {book.kind === 'WEBNOVEL' ? '웹소설' : '일반서적'} · {book.language}
        </p>
      </div>
    </div>
  );
}

function Center({ children }) {
  return <p style={{ textAlign: 'center', color: '#999', padding: 40 }}>{children}</p>;
}
