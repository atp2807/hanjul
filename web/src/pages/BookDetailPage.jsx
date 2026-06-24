import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';

import { useAuth } from '../auth/AuthContext';
import { getLoginUrl } from '../services/api/auth';
import { getStoreDetail } from '../services/api/books';
import { confirmPayment, createOrder } from '../services/api/orders';
import { addReview, getReviews } from '../services/api/reviews';

export function BookDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [book, setBook] = useState(null);
  const [error, setError] = useState(null);
  const [buying, setBuying] = useState(false);
  const [reviews, setReviews] = useState(null);
  const [rating, setRating] = useState(5);
  const [reviewBody, setReviewBody] = useState('');

  useEffect(() => {
    getStoreDetail(id).then(setBook).catch((e) => setError(e.message));
  }, [id]);

  const loadReviews = () => getReviews(id).then(setReviews).catch(() => {});
  useEffect(() => { loadReviews(); }, [id]);

  async function submitReview() {
    try {
      await addReview(id, rating, reviewBody);
      setReviewBody('');
      await loadReviews();
    } catch (e) {
      setError(e.status === 403 ? '구매한 독자만 리뷰할 수 있어요.' : `리뷰 실패: ${e.message}`);
    }
  }

  async function handleBuy() {
    if (!user) {
      // 미로그인 → Google 로그인으로
      const { authorizationUrl } = await getLoginUrl('google');
      window.location.href = authorizationUrl;
      return;
    }
    setBuying(true);
    setError(null);
    try {
      const order = await createOrder(book.id); // 금액은 서버가 책 가격에서 도출
      await confirmPayment(order.id, 'demo'); // 데모 스텁 결제
      navigate(`/read/${book.id}`); // 구매 완료 → 전체 읽기
    } catch (e) {
      if (e.status === 409) {
        navigate(`/read/${book.id}`); // 이미 소유 → 바로 읽기
        return;
      }
      setError(`구매 실패: ${e.message}`);
    } finally {
      setBuying(false);
    }
  }

  if (error && !book) return <Center>불러오기 실패: {error}</Center>;
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
        {book.authorId && (
          <Link to={`/authors/${book.authorId}`} style={{ fontSize: 13, color: '#555' }}>작가 페이지 →</Link>
        )}
        {book.category && (
          <span style={{ display: 'inline-block', fontSize: 12, color: '#555', background: '#f1f2f4', borderRadius: 999, padding: '3px 10px' }}>
            {book.category}
          </span>
        )}
        {book.description && (
          <p style={{ color: '#444', marginTop: 14, whiteSpace: 'pre-wrap', lineHeight: 1.6 }}>{book.description}</p>
        )}
        {(() => {
          const onSale = book.discountAmt != null && book.discountUntil && new Date(book.discountUntil).getTime() > Date.now();
          const eff = onSale ? book.discountAmt : book.priceAmt;
          return (
            <p data-testid="price" style={{ fontSize: 20, fontWeight: 700, margin: '16px 0' }}>
              {eff != null ? `${eff.toLocaleString()}원` : '무료'}
              {onSale && (
                <span style={{ textDecoration: 'line-through', color: '#aaa', fontSize: 14, marginLeft: 8, fontWeight: 400 }}>
                  {book.priceAmt.toLocaleString()}원
                </span>
              )}
              {onSale && <span style={{ color: '#dc2626', fontSize: 13, marginLeft: 8 }}>기간 할인</span>}
            </p>
          );
        })()}
        <div style={{ display: 'flex', gap: 10 }}>
          <Link
            to={`/read/${book.id}`}
            style={{ padding: '10px 20px', background: '#111', color: '#fff', borderRadius: 8, textDecoration: 'none', fontWeight: 600 }}
          >
            읽기
          </Link>
          {book.priceAmt > 0 && (
            <button
              onClick={handleBuy}
              disabled={buying}
              style={{ padding: '10px 20px', borderRadius: 8, border: '1px solid #ddd', fontWeight: 600 }}
            >
              {buying ? '구매 중…' : user ? '구매' : '로그인하고 구매'}
            </button>
          )}
        </div>
        {error && <p style={{ color: 'crimson', marginTop: 12 }}>{error}</p>}
        <p style={{ color: '#aaa', fontSize: 12, marginTop: 24 }}>
          {book.kind === 'WEBNOVEL' ? '웹소설' : '일반서적'} · {book.language}
        </p>

        <section style={{ marginTop: 28, borderTop: '1px solid #eee', paddingTop: 18 }}>
          <h3 style={{ fontSize: 16, margin: '0 0 12px' }}>
            리뷰{reviews && reviews.count > 0 ? ` · ★${reviews.average} (${reviews.count})` : ''}
          </h3>
          {user && (
            <div data-testid="review-form" style={{ marginBottom: 16 }}>
              <select value={rating} onChange={(e) => setRating(Number(e.target.value))} aria-label="평점" style={{ padding: '6px 10px', border: '1px solid #ddd', borderRadius: 6 }}>
                {[5, 4, 3, 2, 1].map((n) => (
                  <option key={n} value={n}>{'★'.repeat(n)} {n}</option>
                ))}
              </select>
              <textarea
                value={reviewBody}
                onChange={(e) => setReviewBody(e.target.value)}
                placeholder="리뷰를 남겨주세요 (선택)"
                rows={2}
                style={{ display: 'block', width: '100%', boxSizing: 'border-box', marginTop: 8, padding: 10, border: '1px solid #ddd', borderRadius: 8, fontFamily: 'inherit' }}
              />
              <button onClick={submitReview} style={{ marginTop: 8, padding: '8px 16px', borderRadius: 8, background: '#111', color: '#fff', fontWeight: 600, border: 'none', cursor: 'pointer' }}>
                리뷰 등록
              </button>
            </div>
          )}
          <ul data-testid="review-list" style={{ listStyle: 'none', padding: 0, margin: 0 }}>
            {reviews?.items.map((r) => (
              <li key={r.id} style={{ padding: '8px 0', borderTop: '1px solid #f3f3f3' }}>
                <span style={{ color: '#f59e0b' }}>{'★'.repeat(r.rating)}</span>{' '}
                <b style={{ fontSize: 13 }}>{r.author || '익명'}</b>
                {r.updatedAt && <span style={{ marginLeft: 6, fontSize: 12, color: '#aaa' }}>(수정됨)</span>}
                {r.body && <p style={{ margin: '4px 0 0', color: '#444' }}>{r.body}</p>}
              </li>
            ))}
            {reviews && reviews.count === 0 && <li style={{ color: '#aaa', fontSize: 13 }}>아직 리뷰가 없어요.</li>}
          </ul>
        </section>
      </div>
    </div>
  );
}

function Center({ children }) {
  return <p style={{ textAlign: 'center', color: '#999', padding: 40 }}>{children}</p>;
}
