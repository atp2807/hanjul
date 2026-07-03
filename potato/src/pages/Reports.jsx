import { useCallback, useEffect, useState } from 'react';

import { api } from '../api';
import { T } from '../theme';
import { Badge, Button, Icon, PageHeader } from '../ui.jsx';

const TARGET = {
  BOOK: { label: '책', tone: 'info' },
  REVIEW: { label: '리뷰', tone: 'warn' },
  ACCOUNT: { label: '유저', tone: 'danger' },
};

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
    const resolution = window.prompt(action === 'RESOLVE' ? '조치 내용 (선택)' : '기각 사유 (선택)');
    if (resolution === null) return;
    try { await api.resolveReport(id, action, resolution); }
    catch { setError('신고 처리에 실패했습니다. 잠시 후 다시 시도하세요.'); return; }
    load();
  }

  return (
    <div>
      <PageHeader
        title="신고 큐"
        subtitle="접수된 신고를 검토하고 조치하세요."
        right={<Badge tone="danger" style={{ fontSize: 13, padding: '6px 14px' }}>{`대기 ${reports.length}건`}</Badge>}
      />
      {error && <div style={{ color: T.danger, marginBottom: 12 }}>{error}</div>}

      {reports.length === 0 && (
        <div
          style={{
            background: T.surface,
            borderRadius: T.radius.card,
            border: `1px solid ${T.borderSoft}`,
            padding: 28,
            color: T.muted,
          }}
        >
          미처리 신고가 없습니다.
        </div>
      )}

      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {reports.map((r) => {
          const t = TARGET[r.targetType] || { label: r.targetType, tone: 'neutral' };
          return (
            <div
              key={r.id}
              style={{
                background: T.surface,
                border: `1px solid ${T.borderSoft}`,
                borderRadius: 16,
                padding: '20px 24px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: 16 }}>
                <span
                  style={{
                    width: 42,
                    height: 42,
                    borderRadius: 12,
                    background: T.dangerBg,
                    color: T.danger,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    flexShrink: 0,
                  }}
                >
                  <Icon name="reports" size={20} />
                </span>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 9, marginBottom: 8 }}>
                    <Badge tone={t.tone}>{t.label} 신고</Badge>
                    <span style={{ fontSize: 12.5, color: T.faint, fontFamily: 'monospace' }}>
                      {r.targetId}
                    </span>
                  </div>
                  <div
                    style={{
                      background: T.rowTint,
                      borderRadius: 11,
                      padding: '13px 15px',
                      fontSize: 13.5,
                      color: T.textSoft,
                      lineHeight: 1.7,
                    }}
                  >
                    {r.reason}
                  </div>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8, width: 130, flexShrink: 0 }}>
                  <Button kind="primary" onClick={() => resolve(r.id, 'RESOLVE')} style={{ textAlign: 'center' }}>
                    조치 완료
                  </Button>
                  <Button onClick={() => resolve(r.id, 'DISMISS')} style={{ textAlign: 'center' }}>
                    기각
                  </Button>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
