import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import { getAuthor } from '../services/api/authors';

export function AuthorPage() {
  const { id } = useParams();
  const [author, setAuthor] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    getAuthor(id).then(setAuthor).catch((e) => setError(e.status === 404 ? '작가를 찾을 수 없어요.' : e.message));
  }, [id]);

  if (error) return <Center>{error}</Center>;
  if (!author) return <Center>불러오는 중…</Center>;

  return (
    <div style={{ maxWidth: 980, margin: '0 auto', padding: '28px 24px' }}>
      <h1 data-testid="author-name" style={{ margin: '0 0 6px', fontWeight: 700 }}>{author.displayName || '작가'}</h1>
      {author.bio && <p data-testid="author-bio" style={{ color: '#555', whiteSpace: 'pre-wrap', lineHeight: 1.6, marginTop: 0 }}>{author.bio}</p>}

      <h2 style={{ fontSize: 16, marginTop: 28 }}>출판작 {author.books.length}</h2>
      {author.books.length === 0 && <p style={{ color: '#999' }}>아직 출판한 책이 없어요.</p>}
      <div data-testid="author-books" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: 20 }}>
        {author.books.map((b) => (
          <Link key={b.id} to={`/books/${b.id}`} style={{ textDecoration: 'none', color: 'inherit' }}>
            {b.coverUrl ? (
              <img src={b.coverUrl} alt={b.title} style={{ width: '100%', aspectRatio: '3/4', objectFit: 'cover', borderRadius: 8 }} />
            ) : (
              <div style={{ width: '100%', aspectRatio: '3/4', borderRadius: 8, background: 'linear-gradient(135deg,#f3f4f6,#e5e7eb)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#9ca3af', fontSize: 13, padding: 12, textAlign: 'center', boxSizing: 'border-box' }}>{b.title}</div>
            )}
            <div style={{ marginTop: 8, fontWeight: 600, fontSize: 15 }}>{b.title}</div>
            <div style={{ color: '#666', fontSize: 13 }}>{b.priceAmt != null ? `${b.priceAmt.toLocaleString()}원` : '무료'}</div>
          </Link>
        ))}
      </div>
    </div>
  );
}

function Center({ children }) {
  return <p style={{ textAlign: 'center', color: '#999', padding: 40 }}>{children}</p>;
}
