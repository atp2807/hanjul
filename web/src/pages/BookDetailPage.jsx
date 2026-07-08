import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';

import { useApiQuery } from '@hanjul/lib';

import { useAuth } from '../auth/AuthContext';
import { useIsMobile } from '../hooks/useIsMobile';
import { Stars } from '../components/Stars';
import { Icon } from '../components/Icon';
import { Avatar, Cover, ErrorNotice } from '../components/ui';
import { getLoginUrl } from '../services/api/auth';
import { getStoreDetail } from '../services/api/books';
import { confirmPayment, createOrder, getPaymentConfig } from '../services/api/orders';
import { addReview, getReviews } from '../services/api/reviews';
import { T } from '../theme';


export function BookDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const isMobile = useIsMobile();
  const [book, setBook] = useState(null);
  const [error, setError] = useState(null);
  const [buying, setBuying] = useState(false);
  const [consent, setConsent] = useState(false);
  const [rating, setRating] = useState(5);
  const [reviewBody, setReviewBody] = useState('');

  useEffect(() => {
    getStoreDetail(id).then(setBook).catch((e) => setError(e.message));
  }, [id]);

  const { data: reviews, error: reviewsError, reload: loadReviews } = useApiQuery(() => getReviews(id), [id]);

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
      const { authorizationUrl } = await getLoginUrl('google');
      window.location.href = authorizationUrl;
      return;
    }
    if (!consent) {
      setError('전자책 청약철회 제한에 동의해 주세요.');
      return;
    }
    setBuying(true);
    setError(null);
    try {
      const cfg = await getPaymentConfig();
      const order = await createOrder(book.id, 'SELF', true); // 금액은 서버가 책 가격에서 도출
      if (cfg.demo || !cfg.tossClientKey) {
        await confirmPayment(order.id, 'demo'); // 데모 모드 — PG 우회
        navigate(`/read/${book.id}`);
        return;
      }
      // 실 결제 — 토스 결제위젯 체크아웃으로. 주문정보는 라우터 state로 전달(URL에 금액 노출 X).
      navigate('/checkout', {
        state: { orderId: order.id, amount: order.amountAmt, orderName: book.title, bookId: book.id },
      });
    } catch (e) {
      if (e.status === 409) {
        navigate(`/read/${book.id}`); // 이미 소유 → 바로 읽기
        return;
      }
      setError(`구매 실패: ${e.message || e.code}`);
      setBuying(false);
    }
  }

  if (error && !book) return <Center>불러오기 실패: {error}</Center>;
  if (!book) return <Center>불러오는 중…</Center>;

  const onSale = book.discountAmt != null && book.discountUntil && new Date(book.discountUntil).getTime() > Date.now();
  const eff = onSale ? book.discountAmt : book.priceAmt;
  const isPaid = book.priceAmt > 0;

  return (
    <div style={{ maxWidth: 1080, margin: '0 auto', padding: isMobile ? '20px 16px 48px' : '30px 40px 60px' }}>
      <div style={{ fontSize: 13, color: T.muted, marginBottom: 24 }}>
        <Link to="/" style={{ color: T.muted, textDecoration: 'none' }}>서점</Link>
        {book.category && <> &nbsp;›&nbsp; {book.category}</>} &nbsp;›&nbsp;{' '}
        <span style={{ color: T.textMid }}>{book.title}</span>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : '340px 1fr', gap: isMobile ? 28 : 48 }}>
        {/* 표지 + 구매 박스 */}
        <div>
          <Cover url={book.coverUrl} title={book.title} radius={16} labelSize={22} style={{ boxShadow: '0 30px 50px -22px rgba(12,58,50,0.5)' }} />
          <div style={{ background: T.surface, borderRadius: 18, padding: 24, marginTop: 20, boxShadow: '0 1px 3px rgba(12,58,50,0.06)' }}>
            <p data-testid="price" style={{ margin: 0, display: 'flex', alignItems: 'baseline', gap: 8, flexWrap: 'wrap' }}>
              <span style={{ fontSize: 28, fontWeight: 800, color: T.ink }}>{eff != null ? `${eff.toLocaleString()}원` : '무료'}</span>
              {onSale && <span style={{ fontSize: 14, color: '#a8b5af', textDecoration: 'line-through' }}>{book.priceAmt.toLocaleString()}원</span>}
              {onSale && <span style={{ fontSize: 13, color: '#dc2626', fontWeight: 600 }}>기간 할인</span>}
            </p>
            <div style={{ fontSize: 13, color: '#297961', fontWeight: 600, marginTop: 4 }}>전자책 · 즉시 다운로드</div>
            {isPaid && user && (
              <label
                data-testid="withdrawal-consent"
                style={{ display: 'flex', gap: 8, alignItems: 'flex-start', marginTop: 16, fontSize: 12.5, color: T.textMid, lineHeight: 1.55, cursor: 'pointer' }}
              >
                <input
                  type="checkbox"
                  checked={consent}
                  onChange={(e) => setConsent(e.target.checked)}
                  style={{ marginTop: 2, flexShrink: 0 }}
                />
                <span>
                  전자책은 열람·다운로드가 시작되면 청약철회가 제한됩니다. 이에 동의합니다.{' '}
                  <Link to="/legal/refund" style={{ color: T.ink, fontWeight: 600 }}>
                    환불 정책
                  </Link>
                </span>
              </label>
            )}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginTop: isPaid && user ? 12 : 18 }}>
              {isPaid ? (
                <button onClick={handleBuy} disabled={buying || (!!user && !consent)} style={primaryBtn}>
                  {buying ? '구매 중…' : user ? '바로 구매' : '로그인하고 구매'}
                </button>
              ) : (
                <Link to={`/read/${book.id}`} style={{ ...primaryBtn, textDecoration: 'none', display: 'block' }}>무료로 읽기</Link>
              )}
              <Link to={`/read/${book.id}`} style={{ ...subBtn, display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: 4 }}>미리보기 <Icon name="chevron" size={14} stroke="currentColor" /></Link>
            </div>
            {error && <p style={{ color: 'crimson', fontSize: 13, marginTop: 12 }}>{error}</p>}
          </div>
        </div>

        {/* 상세 */}
        <div>
          {book.category && (
            <span style={{ display: 'inline-block', padding: '5px 12px', background: '#e3f3ec', borderRadius: 999, fontSize: 12, fontWeight: 700, color: '#297961' }}>
              {book.category}
            </span>
          )}
          <h1 style={{ margin: '16px 0 8px', fontSize: 38, fontWeight: 800, letterSpacing: '-0.03em', color: T.ink, lineHeight: 1.2 }}>{book.title}</h1>
          {book.subtitle && <p style={{ margin: '0 0 6px', fontSize: 16, color: T.textMid }}>{book.subtitle}</p>}
          {book.authorId && (
            <Link to={`/authors/${book.authorId}`} style={{ fontSize: 16, color: T.textMid, fontWeight: 600, textDecoration: 'none' }}>
              {book.authorName ? `${book.authorName} 지음` : <span style={{ display: 'inline-flex', alignItems: 'center', gap: 3 }}>작가 페이지 <Icon name="chevron" size={13} stroke="currentColor" /></span>}
            </Link>
          )}
          {reviews && reviews.count > 0 && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginTop: 16 }}>
              <Stars value={reviews.average} size={17} />
              <span style={{ fontSize: 14, fontWeight: 700, color: T.ink }}>{reviews.average}</span>
              <span style={{ fontSize: 13, color: T.muted }}>리뷰 {reviews.count.toLocaleString()}개</span>
            </div>
          )}
          {book.description && (
            <p style={{ margin: '26px 0 0', fontSize: 16, lineHeight: 1.85, color: '#3a4843', whiteSpace: 'pre-wrap' }}>{book.description}</p>
          )}

          <div style={{ background: T.surface, borderRadius: 18, padding: 26, marginTop: 30 }}>
            <div style={{ display: 'flex', gap: 30, flexWrap: 'wrap' }}>
              <Meta label="종류" value={book.kind === 'WEBNOVEL' ? '웹소설' : '일반서적'} />
              <Meta label="언어" value={book.language === 'ko' ? '한국어' : book.language} />
              {book.isbn && <Meta label="ISBN" value={book.isbn} />}
            </div>
          </div>

          {/* 리뷰 */}
          <h3 style={{ margin: '40px 0 16px', fontSize: 20, fontWeight: 800, color: T.ink, letterSpacing: '-0.02em' }}>
            독자 리뷰{reviews && reviews.count > 0 ? ` · ${reviews.average} (${reviews.count})` : ''}
          </h3>
          {user && (
            <div data-testid="review-form" style={{ background: T.surface, borderRadius: 16, padding: '18px 20px', marginBottom: 16 }}>
              <select value={rating} onChange={(e) => setRating(Number(e.target.value))} aria-label="평점" style={{ padding: '7px 10px', border: `1px solid ${T.border}`, borderRadius: 8, fontFamily: 'inherit' }}>
                {[5, 4, 3, 2, 1].map((n) => (
                  <option key={n} value={n}>{n}점</option>
                ))}
              </select>
              <textarea
                value={reviewBody}
                onChange={(e) => setReviewBody(e.target.value)}
                placeholder="리뷰를 남겨주세요 (선택)"
                rows={2}
                style={{ display: 'block', width: '100%', boxSizing: 'border-box', marginTop: 8, padding: 10, border: `1px solid ${T.border}`, borderRadius: 8, fontFamily: 'inherit' }}
              />
              <button onClick={submitReview} style={{ ...primaryBtn, marginTop: 8, padding: '9px 18px', width: 'auto' }}>리뷰 등록</button>
            </div>
          )}
          {reviewsError && <ErrorNotice message="리뷰를 불러오지 못했어요." onRetry={loadReviews} style={{ marginBottom: 16 }} />}
          <div data-testid="review-list" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 16 }}>
            {reviews?.items.map((r) => (
              <div key={r.id} style={{ background: T.surface, borderRadius: 16, padding: '22px 24px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
                  <Avatar name={r.author || '익명'} size={30} />
                  <span style={{ fontSize: 14, fontWeight: 700, color: T.ink }}>{r.author || '익명'}</span>
                  {r.source === 'REVIEW_COPY' && (
                    <span title="출판 전 증정본을 받아 작성한 사전 리뷰예요." style={{ fontSize: 11, fontWeight: 700, color: '#297961', background: '#e3f3ec', borderRadius: 999, padding: '2px 8px' }}>
                      서평단
                    </span>
                  )}
                  {r.updatedAt && <span style={{ fontSize: 12, color: T.muted }}>(수정됨)</span>}
                  <span style={{ marginLeft: 'auto' }}><Stars value={r.rating} size={13} /></span>
                </div>
                {r.body && <p style={{ margin: 0, fontSize: 14, lineHeight: 1.75, color: '#52615b' }}>{r.body}</p>}
              </div>
            ))}
            {reviews && reviews.count === 0 && <p style={{ color: T.muted, fontSize: 13 }}>아직 리뷰가 없어요.</p>}
          </div>
        </div>
      </div>
    </div>
  );
}

const primaryBtn = {
  textAlign: 'center', padding: 14, background: T.ink, color: T.inkText, border: 'none',
  borderRadius: 13, fontSize: 15, fontWeight: 700, cursor: 'pointer', width: '100%',
};
const subBtn = {
  textAlign: 'center', padding: 14, background: T.surface, color: T.textMid, border: `1px solid #d6e4de`,
  borderRadius: 13, fontSize: 15, fontWeight: 600, textDecoration: 'none',
};

function Meta({ label, value }) {
  return (
    <div>
      <div style={{ fontSize: 12, color: T.muted, marginBottom: 4 }}>{label}</div>
      <div style={{ fontSize: 15, fontWeight: 700, color: T.ink }}>{value}</div>
    </div>
  );
}

function Center({ children }) {
  return <p style={{ textAlign: 'center', color: T.muted, padding: 40 }}>{children}</p>;
}
