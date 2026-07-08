import { useCallback, useEffect, useState } from 'react';

import { api } from '../api';
import { T } from '../theme';
import { Badge, Button, Card, PageHeader } from '../ui.jsx';

// AGE18 = 연령제한 발행, REPORTED = 신고 접수 — 복수 가능(ReviewQueueItem.reasons).
const REASON_LABEL = {
  AGE18: { label: '연령', tone: 'danger' },
  REPORTED: { label: '신고', tone: 'warn' },
};

export default function ReviewQueue() {
  const [rows, setRows] = useState([]);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setError('');
    try {
      setRows(await api.reviewQueue());
    } catch {
      setError('목록을 불러오지 못했습니다.');
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function takedown(bookId) {
    const reason = window.prompt('강제 비공개 사유 (감사 로그에 기록됩니다)');
    if (reason === null) return;
    try { await api.takedown(bookId, reason); }
    catch { setError('강제 비공개에 실패했습니다. 잠시 후 다시 시도하세요.'); return; }
    load();
  }

  return (
    <div>
      <PageHeader title="검토 큐" subtitle="연령제한·신고 등 사후 검토가 필요한 책을 확인하세요." />
      {error && <div style={{ color: T.danger, marginBottom: 12 }}>{error}</div>}

      <Card style={{ padding: 0, overflow: 'hidden' }}>
        {rows.length === 0 && <div style={{ padding: 24, color: T.muted }}>검토가 필요한 책이 없습니다.</div>}
        {rows.map((b, i) => (
          <div
            key={b.bookId}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 14,
              padding: '16px 20px',
              borderBottom: i < rows.length - 1 ? `1px solid ${T.borderSoft}` : 'none',
            }}
          >
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontSize: 15, fontWeight: 700, color: T.textStrong }}>{b.title}</div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 6, flexWrap: 'wrap' }}>
                {b.reasons.map((r) => {
                  const info = REASON_LABEL[r] || { label: r, tone: 'neutral' };
                  return (
                    <Badge key={r} tone={info.tone}>
                      {info.label}
                    </Badge>
                  );
                })}
                <span style={{ fontSize: 12.5, color: T.muted }}>
                  {b.rating} · {b.publishedAt ? new Date(b.publishedAt).toLocaleString() : '-'}
                </span>
              </div>
            </div>
            <Button kind="danger" onClick={() => takedown(b.bookId)}>
              내리기
            </Button>
          </div>
        ))}
      </Card>
    </div>
  );
}
