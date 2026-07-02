import { useCallback, useEffect, useState } from 'react';

import { api } from '../api';
import { T } from '../theme';
import { Badge, Button, Card, Chip, PageHeader } from '../ui.jsx';

const TABS = [
  ['REQUESTED', '신청됨'],
  ['APPROVED', '승인됨'],
  ['PAID', '지급완료'],
  ['REJECTED', '반려됨'],
];

export default function Payouts() {
  const [status, setStatus] = useState('REQUESTED');
  const [rows, setRows] = useState([]);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setError('');
    try {
      setRows(await api.payouts(status));
    } catch {
      setError('목록을 불러오지 못했습니다.');
    }
  }, [status]);

  useEffect(() => {
    load();
  }, [load]);

  async function act(fn) {
    await fn();
    load();
  }

  return (
    <div>
      <PageHeader title="출금 관리" subtitle="작가 출금 신청을 승인하고 지급을 확정하세요." />
      <div style={{ display: 'flex', gap: 8, marginBottom: 18 }}>
        {TABS.map(([s, label]) => (
          <Chip key={s} active={status === s} onClick={() => setStatus(s)}>
            {label}
          </Chip>
        ))}
      </div>
      {error && <div style={{ color: T.danger, marginBottom: 12 }}>{error}</div>}

      <Card style={{ padding: 0, overflow: 'hidden' }}>
        {rows.length === 0 && <div style={{ padding: 24, color: T.muted }}>해당 상태의 출금이 없습니다.</div>}
        {rows.map((p, i) => (
          <div
            key={p.id}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 14,
              padding: '16px 20px',
              borderBottom: i < rows.length - 1 ? `1px solid ${T.borderSoft}` : 'none',
            }}
          >
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontSize: 16, fontWeight: 800, color: T.ink }}>
                {p.netAmt.toLocaleString()}원
              </div>
              <div style={{ fontSize: 12.5, color: T.muted, marginTop: 2 }}>
                {p.bank || '-'} · {p.accountNoMasked || '-'} · {p.holderName || '-'} · 원천징수{' '}
                {p.withholdingAmt.toLocaleString()}원
              </div>
            </div>
            {p.status === 'REQUESTED' && (
              <>
                <Button kind="primary" onClick={() => act(() => api.approvePayout(p.id))}>
                  승인
                </Button>
                <Button
                  kind="danger"
                  onClick={() => act(() => api.rejectPayout(p.id, window.prompt('반려 사유 (선택)') || null))}
                >
                  반려
                </Button>
              </>
            )}
            {p.status === 'APPROVED' && (
              <Button
                kind="primary"
                onClick={() => act(() => api.payPayout(p.id, window.prompt('이체 메모 (선택)') || null))}
              >
                지급완료
              </Button>
            )}
            {p.status === 'PAID' && <Badge tone="ok">지급완료</Badge>}
            {p.status === 'REJECTED' && <Badge tone="danger">반려됨</Badge>}
          </div>
        ))}
      </Card>
    </div>
  );
}
