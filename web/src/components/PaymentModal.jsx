import { useEffect, useRef } from 'react';

// 토스 결제위젯(iframe) 모달. payment-widget.html 과 postMessage 로 통신.
// 위젯이 SUCCESS{paymentKey} 보내면 onSuccess(paymentKey) 호출.
export function PaymentModal({ clientKey, orderId, orderName, amount, onSuccess, onCancel }) {
  const handledRef = useRef(false);

  useEffect(() => {
    function onMessage(e) {
      // 위젯(iframe)은 same-origin(/payment-widget.html) — 타 origin 메시지는 무시(주입 차단)
      if (e.origin !== window.location.origin) return;
      const d = e.data || {};
      if (d.type === 'SUCCESS' && d.orderId === orderId && !handledRef.current) {
        handledRef.current = true;
        onSuccess(d.paymentKey);
      } else if (d.type === 'CANCEL') {
        onCancel('결제가 취소되었어요.');
      } else if (d.type === 'FAIL' || d.type === 'ERROR') {
        onCancel(d.message || '결제에 실패했어요.');
      }
    }
    window.addEventListener('message', onMessage);
    return () => window.removeEventListener('message', onMessage);
  }, [orderId, onSuccess, onCancel]);

  const params = new URLSearchParams({
    clientKey,
    orderId,
    orderName: orderName || '한줄 ebook',
    amount: String(amount),
  });

  return (
    <div
      onClick={() => onCancel()}
      style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}
    >
      <div onClick={(e) => e.stopPropagation()} style={{ width: 'min(420px, 94vw)', height: 'min(640px, 90vh)', background: '#fff', borderRadius: 16, overflow: 'hidden', position: 'relative' }}>
        <button
          onClick={() => onCancel()}
          aria-label="닫기"
          style={{ position: 'absolute', top: 10, right: 12, zIndex: 2, border: 'none', background: 'transparent', fontSize: 20, cursor: 'pointer', color: '#888' }}
        >
          ✕
        </button>
        <iframe
          title="결제"
          data-testid="payment-iframe"
          src={`/payment-widget.html?${params.toString()}`}
          style={{ width: '100%', height: '100%', border: 'none' }}
        />
      </div>
    </div>
  );
}
