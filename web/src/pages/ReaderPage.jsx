import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import { useAuth } from '../auth/AuthContext';
import { Reader } from '../reader/Reader';
import { getLoginUrl } from '../services/api/auth';
import { flattenBlocks, getBookContent } from '../services/api/books';
import { confirmPayment, createOrder } from '../services/api/orders';
import { T } from '../theme';

export function ReaderPage() {
  const { id } = useParams();
  const { user } = useAuth();
  const [blocks, setBlocks] = useState(null);
  const [isPreview, setIsPreview] = useState(false);
  const [price, setPrice] = useState(null);
  const [error, setError] = useState(null);
  const [buying, setBuying] = useState(false);
  const [memo, setMemo] = useState('');

  useEffect(() => { setMemo(localStorage.getItem(`hanjul-reader-memo-${id}`) || ''); }, [id]);
  function updateMemo(v) {
    setMemo(v);
    localStorage.setItem(`hanjul-reader-memo-${id}`, v);
  }

  async function load() {
    const content = await getBookContent(id);
    setBlocks(flattenBlocks(content));
    setIsPreview(content.isPreview);
    setPrice(content.priceAmt);
  }

  useEffect(() => {
    load().catch((e) => setError(e.message));
  }, [id]);

  async function handleBuy() {
    if (!user) {
      const { authorizationUrl } = await getLoginUrl('google');
      window.location.href = authorizationUrl;
      return;
    }
    setBuying(true);
    setError(null);
    try {
      const order = await createOrder(id);
      await confirmPayment(order.id, 'demo');
      await load(); // 구매 완료 → 전체로 다시 로드
    } catch (e) {
      if (e.status === 409) {
        await load(); // 이미 소유 → 재로드
        return;
      }
      setError(`구매 실패: ${e.message}`);
    } finally {
      setBuying(false);
    }
  }

  return (
    <div style={{ maxWidth: 680, margin: '0 auto', padding: '20px 16px 40px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 14, fontSize: 14, color: T.textSoft, fontWeight: 600, marginBottom: 18 }}>
        <Link to="/library" style={{ color: T.textSoft, textDecoration: 'none' }}>‹ 서재로</Link>
      </div>
      {error && <p style={{ color: 'crimson' }}>{error}</p>}
      {!blocks && !error && <p style={{ color: T.muted }}>불러오는 중…</p>}
      {blocks && <Reader blocks={blocks} bookId={id} />}

      {blocks && (
        <section style={{ marginTop: 22 }}>
          <div style={{ fontSize: 13, color: T.muted, marginBottom: 6 }}>독서 메모 (이 기기에 저장)</div>
          <textarea
            data-testid="reader-memo"
            value={memo}
            onChange={(e) => updateMemo(e.target.value)}
            rows={4}
            placeholder="기억하고 싶은 구절·생각을 적어두세요"
            style={{ width: '100%', boxSizing: 'border-box', padding: 12, border: `1px solid ${T.border}`, borderRadius: 10, fontFamily: 'inherit', fontSize: 14, background: T.surface }}
          />
        </section>
      )}

      {isPreview && (
        <div style={{ marginTop: 16, padding: 22, border: `1px solid ${T.border}`, borderRadius: 16, textAlign: 'center', background: T.surface }}>
          <p style={{ margin: '0 0 12px', color: T.textMid }}>
            여기까지 미리보기예요{price != null ? ` · ${price.toLocaleString()}원` : ''}
          </p>
          <button
            onClick={handleBuy}
            disabled={buying}
            style={{ padding: '13px 28px', borderRadius: 13, background: T.ink, color: T.inkText, fontWeight: 700, border: 'none', cursor: 'pointer' }}
          >
            {buying ? '구매 중…' : user ? '구매하고 계속 읽기' : '로그인하고 구매'}
          </button>
        </div>
      )}
    </div>
  );
}
