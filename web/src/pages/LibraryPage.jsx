import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

import { useAuth } from '../auth/AuthContext';
import { getLibrary, refundOrder } from '../services/api/orders';

function Cover({ url, title }) {
  if (url) {
    return <img src={url} alt={title} loading="lazy" style={{ width: '100%', aspectRatio: '3/4', objectFit: 'cover', borderRadius: 8 }} />;
  }
  return (
    <div style={{ width: '100%', aspectRatio: '3/4', borderRadius: 8, background: 'linear-gradient(135deg,#f3f4f6,#e5e7eb)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#9ca3af', fontSize: 13, padding: 12, textAlign: 'center', boxSizing: 'border-box' }}>
      {title}
    </div>
  );
}

export function LibraryPage() {
  const { user, loading } = useAuth();
  const [items, setItems] = useState([]);
  const [fetching, setFetching] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (loading) return;
    if (!user) {
      setFetching(false);
      return;
    }
    getLibrary()
      .then(setItems)
      .catch((e) => setError(e.message))
      .finally(() => setFetching(false));
  }, [user, loading]);

  async function handleRefund(orderId) {
    if (!window.confirm('이 책을 환불할까요? 환불하면 서재에서 사라지고 다시 읽을 수 없어요.')) return;
    try {
      await refundOrder(orderId);
      setItems((prev) => prev.filter((b) => b.orderId !== orderId));
    } catch (e) {
      setError(e.status === 409 ? '이미 환불됐거나 환불할 수 없는 주문이에요.' : `환불 실패: ${e.message}`);
    }
  }

  if (loading || fetching) return <Center>불러오는 중…</Center>;
  if (!user) return <Center>로그인이 필요해요.</Center>;

  return (
    <div style={{ maxWidth: 980, margin: '0 auto', padding: '28px 24px' }}>
      <h2 style={{ marginTop: 0, fontWeight: 700 }}>내 서재</h2>
      {error && <p style={{ color: 'crimson' }}>{error}</p>}
      {items.length === 0 && <p style={{ color: '#999' }}>아직 구매한 책이 없어요.</p>}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: 20 }}>
        {items.map((b) => (
          <div key={b.bookId}>
            <Link to={`/read/${b.bookId}`} style={{ textDecoration: 'none', color: 'inherit' }}>
              <Cover url={b.coverUrl} title={b.title} />
              <div style={{ marginTop: 8, fontWeight: 600, fontSize: 15 }}>{b.title}</div>
            </Link>
            <button
              onClick={() => handleRefund(b.orderId)}
              style={{ marginTop: 6, fontSize: 12, color: '#999', background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}
            >
              환불
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

function Center({ children }) {
  return <p style={{ textAlign: 'center', color: '#999', padding: 40 }}>{children}</p>;
}
