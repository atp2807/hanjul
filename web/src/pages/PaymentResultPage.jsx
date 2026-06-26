import { useEffect, useRef, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';

import { confirmPayment } from '../services/api/orders';
import { T } from '../theme';

// 토스 결제창(v1) successUrl/failUrl 착지점.
// 성공: ?paymentKey=&orderId=&amount=&bookId= → 백엔드 confirm → 읽기로.
// 실패: ?code=&message=&bookId= → 사유 표시.
export function PaymentResultPage() {
  const [sp] = useSearchParams();
  const navigate = useNavigate();
  const [state, setState] = useState('처리 중…');
  const ran = useRef(false);

  const paymentKey = sp.get('paymentKey');
  const orderId = sp.get('orderId');
  const bookId = sp.get('bookId');
  const failCode = sp.get('code');

  useEffect(() => {
    if (ran.current) return;
    ran.current = true;

    if (failCode) {
      setState(`결제 실패: ${sp.get('message') || failCode}`);
      return;
    }
    if (!paymentKey || !orderId) {
      setState('잘못된 접근이에요.');
      return;
    }
    confirmPayment(orderId, paymentKey)
      .then(() => {
        setState('결제 완료! 책으로 이동할게요…');
        navigate(bookId ? `/read/${bookId}` : '/library', { replace: true });
      })
      .catch((e) => {
        setState(e.status === 402 ? '결제 승인에 실패했어요.' : `결제 처리 실패: ${e.message}`);
      });
  }, [paymentKey, orderId, bookId, failCode, sp, navigate]);

  return (
    <div style={{ maxWidth: 480, margin: '80px auto', textAlign: 'center', padding: 24 }}>
      <div style={{ background: T.surface, borderRadius: 20, padding: '40px 28px', boxShadow: T.shadow }}>
        <p style={{ fontSize: 16, color: T.textStrong, margin: 0 }} data-testid="payment-result">{state}</p>
        <Link to={bookId ? `/books/${bookId}` : '/'} style={{ display: 'inline-block', marginTop: 16, color: T.textMid, fontWeight: 600 }}>
          돌아가기
        </Link>
      </div>
    </div>
  );
}
