import { useEffect, useRef, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';

import { ANONYMOUS, loadTossPayments } from '@tosspayments/tosspayments-sdk';

import { useAuth } from '../auth/AuthContext';
import { getPaymentConfig } from '../services/api/orders';
import { T } from '../theme';

// 토스 결제위젯(v2) 체크아웃.
// BookDetailPage가 주문 생성 후 navigate('/checkout', { state: {orderId, amount, orderName, bookId} }).
// 위젯(결제수단 선택 + 약관)을 렌더 → '결제하기' → widgets.requestPayment() → 토스 인증창 →
// successUrl(/payment/result?bookId=)으로 복귀 → 거기서 서버 confirm(결제창 시절과 동일).
export function CheckoutPage() {
  const { state } = useLocation();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [error, setError] = useState(null);
  const [ready, setReady] = useState(false);
  const [paying, setPaying] = useState(false);
  const widgetsRef = useRef(null);
  const started = useRef(false); // StrictMode 이중 effect + 위젯 중복 렌더 방지

  const order = state && state.orderId ? state : null;

  useEffect(() => {
    if (started.current) return;
    started.current = true;

    if (!order) {
      setError('잘못된 접근이에요. 책 상세에서 다시 시도해 주세요.');
      return;
    }

    (async () => {
      try {
        const cfg = await getPaymentConfig();
        if (cfg.demo || !cfg.tossClientKey) {
          // 데모/키 없음이면 위젯을 못 띄움 — 상세 페이지가 이 경로로 안 보내지만 방어.
          setError('결제 설정이 준비되지 않았어요.');
          return;
        }
        const toss = await loadTossPayments(cfg.tossClientKey);
        const widgets = toss.widgets({ customerKey: user?.id || ANONYMOUS });
        await widgets.setAmount({ currency: 'KRW', value: order.amount });
        await Promise.all([
          widgets.renderPaymentMethods({ selector: '#payment-method', variantKey: 'DEFAULT' }),
          widgets.renderAgreement({ selector: '#agreement', variantKey: 'AGREEMENT' }),
        ]);
        widgetsRef.current = widgets;
        setReady(true);
      } catch (e) {
        setError(`결제 위젯을 불러오지 못했어요: ${e.message || e.code}`);
      }
    })();
  }, [order, user]);

  async function pay() {
    if (!widgetsRef.current) return;
    setPaying(true);
    setError(null);
    try {
      const successUrl = `${window.location.origin}/payment/result?bookId=${order.bookId}`;
      await widgetsRef.current.requestPayment({
        orderId: order.orderId,
        orderName: order.orderName,
        successUrl,
        failUrl: successUrl,
        customerName: user?.name || undefined,
      });
      // requestPayment는 성공 시 페이지를 토스로 리다이렉트하므로 이 아래는 실행되지 않음.
    } catch (e) {
      if (e.code === 'USER_CANCEL' || e.code === 'PAY_PROCESS_CANCELED') {
        setPaying(false);
        return;
      }
      setError(`결제를 시작하지 못했어요: ${e.message || e.code}`);
      setPaying(false);
    }
  }

  if (error) {
    return (
      <div style={wrap}>
        <div style={card}>
          <p style={{ fontSize: 15, color: 'crimson', margin: 0 }} data-testid="checkout-error">{error}</p>
          <button onClick={() => navigate(-1)} style={{ ...primaryBtn, marginTop: 18 }}>돌아가기</button>
        </div>
      </div>
    );
  }

  return (
    <div style={wrap}>
      <h1 style={{ fontSize: 24, fontWeight: 800, color: T.ink, letterSpacing: '-0.02em', margin: '0 0 4px' }}>결제</h1>
      {order && (
        <p style={{ fontSize: 14, color: T.textMid, margin: '0 0 20px' }}>
          {order.orderName} · <strong style={{ color: T.ink }}>{order.amount?.toLocaleString()}원</strong>
        </p>
      )}
      <div style={card}>
        <div id="payment-method" />
        <div id="agreement" style={{ marginTop: 12 }} />
        <button onClick={pay} disabled={!ready || paying} style={{ ...primaryBtn, marginTop: 20 }} data-testid="pay-button">
          {paying ? '결제 진행 중…' : ready ? `${order?.amount?.toLocaleString()}원 결제하기` : '불러오는 중…'}
        </button>
        <Link to={order?.bookId ? `/books/${order.bookId}` : '/'} style={{ display: 'block', textAlign: 'center', marginTop: 14, color: T.textMid, fontWeight: 600, fontSize: 14 }}>
          취소하고 돌아가기
        </Link>
      </div>
    </div>
  );
}

const wrap = { maxWidth: 560, margin: '40px auto', padding: '0 20px 60px' };
const card = { background: T.surface, borderRadius: 20, padding: '28px 24px', boxShadow: '0 1px 3px rgba(12,58,50,0.06)' };
const primaryBtn = {
  textAlign: 'center', padding: 14, background: T.ink, color: T.inkText, border: 'none',
  borderRadius: 13, fontSize: 15, fontWeight: 700, cursor: 'pointer', width: '100%',
};
