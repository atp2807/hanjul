import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { api } from '../api';
import { T } from '../theme';
import { Card, Icon, PageHeader } from '../ui.jsx';

const KPIS = [
  { key: 'accounts', label: '가입 계정', suffix: '명' },
  { key: 'booksTotal', label: '전체 책', suffix: '권' },
  { key: 'booksPublished', label: '출판중', suffix: '권' },
  { key: 'booksBlocked', label: '차단(takedown)', suffix: '권', tone: T.danger },
];

function Kpi({ label, value, suffix, tone }) {
  return (
    <Card style={{ padding: '22px 24px' }}>
      <div style={{ fontSize: 13, color: T.muted }}>{label}</div>
      <div style={{ fontSize: 27, fontWeight: 800, color: tone || T.ink, marginTop: 8, letterSpacing: '-0.02em' }}>
        {value ?? '–'}
        <span style={{ fontSize: 15, fontWeight: 600, marginLeft: 2 }}>{value != null ? suffix : ''}</span>
      </div>
    </Card>
  );
}

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    api.dashboard().then(setStats).catch(() => setError('통계를 불러오지 못했습니다.'));
  }, []);

  const queue = [
    {
      icon: 'reports',
      label: '신고 처리 대기',
      sub: '책·리뷰·유저 신고',
      count: stats?.reportsOpen ?? 0,
      tone: T.danger,
      bg: T.dangerBg,
      to: '/reports',
    },
    {
      icon: 'moderation',
      label: '강제 비공개된 책',
      sub: 'takedown 상태',
      count: stats?.booksBlocked ?? 0,
      tone: T.warn,
      bg: T.warnBg,
      to: '/moderation',
    },
  ];

  return (
    <div>
      <PageHeader title="운영 대시보드" subtitle="플랫폼 현황을 한눈에 살펴보세요." />
      {error && <div style={{ color: T.danger, marginBottom: 12 }}>{error}</div>}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 16, marginBottom: 22 }}>
        {KPIS.map((k) => (
          <Kpi key={k.key} label={k.label} value={stats?.[k.key]} suffix={k.suffix} tone={k.tone} />
        ))}
      </div>

      <Card style={{ padding: '24px 26px' }}>
        <div style={{ fontSize: 16, fontWeight: 800, color: T.ink, marginBottom: 16 }}>오늘 처리할 일</div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 9 }}>
          {queue.map((q) => (
            <div
              key={q.to}
              onClick={() => navigate(q.to)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 13,
                padding: '13px 14px',
                background: q.count > 0 ? q.bg : T.rowTint,
                borderRadius: 13,
                cursor: 'pointer',
              }}
            >
              <span
                style={{
                  width: 36,
                  height: 36,
                  borderRadius: 11,
                  background: '#fff',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: q.count > 0 ? q.tone : T.faint,
                }}
              >
                <Icon name={q.icon} size={18} />
              </span>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 14, fontWeight: 700, color: T.textStrong }}>{q.label}</div>
                <div style={{ fontSize: 12, color: T.muted, marginTop: 1 }}>{q.sub}</div>
              </div>
              <span style={{ fontSize: 18, fontWeight: 800, color: q.count > 0 ? q.tone : T.faint }}>
                {q.count}
              </span>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
