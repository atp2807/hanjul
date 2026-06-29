import { useCallback, useEffect, useState } from 'react';

import { api } from '../api';
import { T } from '../theme';
import { Badge, Button, Card } from '../ui.jsx';

export default function Reports() {
  const [reports, setReports] = useState([]);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setError('');
    try {
      setReports(await api.reports('OPEN'));
    } catch {
      setError('신고를 불러오지 못했습니다.');
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function resolve(id, action) {
    const resolution = window.prompt(
      action === 'RESOLVE' ? '조치 내용 (선택)' : '기각 사유 (선택)',
    );
    if (resolution === null) return;
    await api.resolveReport(id, action, resolution);
    load();
  }

  return (
    <div>
      <h1 style={{ fontSize: 22, color: T.textStrong, marginTop: 0 }}>신고 큐</h1>
      {error && <div style={{ color: T.danger, marginBottom: 12 }}>{error}</div>}
      <Card style={{ padding: 0 }}>
        {reports.length === 0 && (
          <div style={{ padding: 20, color: T.muted }}>미처리 신고가 없습니다.</div>
        )}
        {reports.map((r) => (
          <div
            key={r.id}
            style={{ padding: '14px 18px', borderBottom: `1px solid ${T.borderSoft}` }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
              <Badge tone="warn">{r.targetType}</Badge>
              <span style={{ fontSize: 12, color: T.muted, fontFamily: 'monospace' }}>
                {r.targetId}
              </span>
            </div>
            <div style={{ color: T.textStrong, marginBottom: 10 }}>{r.reason}</div>
            <div style={{ display: 'flex', gap: 8 }}>
              <Button kind="primary" onClick={() => resolve(r.id, 'RESOLVE')}>
                조치 완료
              </Button>
              <Button kind="ghost" onClick={() => resolve(r.id, 'DISMISS')}>
                기각
              </Button>
            </div>
          </div>
        ))}
      </Card>
    </div>
  );
}
