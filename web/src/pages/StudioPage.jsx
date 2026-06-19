import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';

import { useAuth } from '../auth/AuthContext';
import { createBook, getMyBooks } from '../services/api/studio';

export const STATUS_LABEL = { DRAFT: '초안', REVIEW: '심사중', PUBLISHED: '출판됨' };

export function StudioPage() {
  const { user, loading } = useAuth();
  const navigate = useNavigate();
  const [items, setItems] = useState([]);
  const [title, setTitle] = useState('');
  const [fetching, setFetching] = useState(true);

  useEffect(() => {
    if (loading) return;
    if (!user) {
      setFetching(false);
      return;
    }
    getMyBooks()
      .then((d) => setItems(d.items))
      .finally(() => setFetching(false));
  }, [user, loading]);

  async function handleCreate(e) {
    e.preventDefault();
    if (!title.trim()) return;
    const { bookId } = await createBook(title.trim());
    navigate(`/studio/${bookId}`);
  }

  if (loading || fetching) return <Center>불러오는 중…</Center>;
  if (!user) return <Center>로그인이 필요해요.</Center>;

  return (
    <div style={{ maxWidth: 980, margin: '0 auto', padding: '28px 24px' }}>
      <h2 style={{ marginTop: 0, fontWeight: 700 }}>작가 스튜디오</h2>
      <form onSubmit={handleCreate} style={{ display: 'flex', gap: 8, marginBottom: 24 }}>
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="새 책 제목"
          style={{ flex: 1, maxWidth: 320, padding: '8px 12px', border: '1px solid #ddd', borderRadius: 8 }}
        />
        <button style={{ padding: '8px 16px', borderRadius: 8, background: '#111', color: '#fff', fontWeight: 600, border: 'none' }}>
          새 책 만들기
        </button>
      </form>

      {items.length === 0 && <p style={{ color: '#999' }}>아직 쓴 책이 없어요. 위에서 만들어보세요.</p>}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 16 }}>
        {items.map((b) => (
          <Link
            key={b.id}
            to={`/studio/${b.id}`}
            style={{ textDecoration: 'none', color: 'inherit', border: '1px solid #eee', borderRadius: 10, padding: 16 }}
          >
            <div style={{ fontWeight: 600, fontSize: 15 }}>{b.title}</div>
            <div style={{ fontSize: 13, color: '#888', marginTop: 6 }}>
              {STATUS_LABEL[b.status] || b.status}
              {b.priceAmt != null ? ` · ${b.priceAmt.toLocaleString()}원` : ''}
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}

function Center({ children }) {
  return <p style={{ textAlign: 'center', color: '#999', padding: 40 }}>{children}</p>;
}
