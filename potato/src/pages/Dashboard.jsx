import { useEffect, useState } from 'react';

import { api } from '../api';
import { T } from '../theme';
import { Card } from '../ui.jsx';

const CARDS = [
  { key: 'accounts', label: '가입 계정' },
  { key: 'booksTotal', label: '전체 책' },
  { key: 'booksPublished', label: '출판중' },
  { key: 'booksBlocked', label: '차단(takedown)', tone: 'danger' },
  { key: 'reportsOpen', label: '미처리 신고', tone: 'warn' },
];

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    api.dashboard().then(setStats).catch(() => setError('통계를 불러오지 못했습니다.'));
  }, []);

  return (
    <div>
      <h1 style={{ fontSize: 22, color: T.textStrong, marginTop: 0 }}>대시보드</h1>
      {error && <div style={{ color: T.danger }}>{error}</div>}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(160px,1fr))', gap: 14 }}>
        {CARDS.map((c) => (
          <Card key={c.key}>
            <div style={{ fontSize: 13, color: T.textSoft, marginBottom: 8 }}>{c.label}</div>
            <div
              style={{
                fontSize: 32,
                fontWeight: 700,
                color: c.tone === 'danger' ? T.danger : c.tone === 'warn' ? T.warn : T.ink,
              }}
            >
              {stats ? stats[c.key] : '–'}
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
