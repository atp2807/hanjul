import { useCallback, useEffect, useState } from 'react';

import { api } from '../api';
import { T } from '../theme';
import { Button, Card, PageHeader } from '../ui.jsx';

export default function Refunds() {
  const [rows, setRows] = useState([]);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setError('');
    try {
      setRows(await api.orders('PAID'));
    } catch {
      setError('목록을 불러오지 못했습니다.');
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function refund(id) {
    const reason = window.prompt('환불 사유 (감사 로그에 기록됩니다)');
    if (reason === null) return;
    try {
      await api.refundOrder(id, reason);
    } catch (e) {
      // load()가 내부에서 setError('')로 시작하므로 반드시 load() 먼저 → 메시지는 그 다음에 설정
      // (순서를 바꾸면 메시지가 load()의 초기화에 곧바로 덮여 사라진다).
      load();
      // 409 = 이미 환불되었거나 결제완료 상태가 아님(경합/재클릭 방지 가드), 402 = PG 취소 자체 실패
      if (e.status === 409) setError('이미 환불되었거나 결제되지 않은 주문입니다. 목록을 갱신했어요.');
      else if (e.status === 402) setError('PG 취소에 실패했습니다. 잠시 후 다시 시도하세요.');
      else setError('환불 처리에 실패했습니다. 잠시 후 다시 시도하세요.');
      return;
    }
    load();
  }

  return (
    <div>
      <PageHeader title="환불 관리" subtitle="결제완료 주문을 조회하고 환불을 집행하세요." />
      {error && <div style={{ color: T.danger, marginBottom: 12 }}>{error}</div>}

      <Card style={{ padding: 0, overflow: 'hidden' }}>
        {rows.length === 0 && <div style={{ padding: 24, color: T.muted }}>결제완료 주문이 없습니다.</div>}
        {rows.map((o, i) => (
          <div
            key={o.id}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 14,
              padding: '16px 20px',
              borderBottom: i < rows.length - 1 ? `1px solid ${T.borderSoft}` : 'none',
            }}
          >
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontSize: 15, fontWeight: 700, color: T.textStrong }}>{o.bookTitle}</div>
              <div style={{ fontSize: 12.5, color: T.muted, marginTop: 2 }}>
                구매자 {o.buyerAccountId} · {o.amountAmt.toLocaleString()}원 ·{' '}
                {o.paidAt ? new Date(o.paidAt).toLocaleString() : '결제 전'}
              </div>
            </div>
            <Button kind="danger" onClick={() => refund(o.id)}>
              환불
            </Button>
          </div>
        ))}
      </Card>
    </div>
  );
}
