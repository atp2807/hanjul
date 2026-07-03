import { useCallback, useEffect, useState } from 'react';

import { api } from '../api';
import { T } from '../theme';
import { Badge, Button, Card, Cover, Field, PageHeader } from '../ui.jsx';

const STATUS_LABEL = { DRAFT: '초안', REVIEW: '심사중', PUBLISHED: '출판중' };

export default function Moderation() {
  const [books, setBooks] = useState([]);
  const [q, setQ] = useState('');
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setError('');
    try {
      setBooks(await api.books({ q }));
    } catch {
      setError('목록을 불러오지 못했습니다.');
    }
  }, [q]);

  useEffect(() => {
    load();
  }, [load]);

  async function takedown(id) {
    const reason = window.prompt('강제 비공개 사유 (감사 로그에 기록됩니다)');
    if (reason === null) return;
    try { await api.takedown(id, reason); }
    catch { setError('강제 비공개에 실패했습니다. 잠시 후 다시 시도하세요.'); return; }
    load();
  }
  async function restore(id) {
    try { await api.restore(id); }
    catch { setError('복원에 실패했습니다. 잠시 후 다시 시도하세요.'); return; }
    load();
  }

  return (
    <div>
      <PageHeader
        title="모더레이션"
        subtitle="문제 콘텐츠를 강제 비공개(takedown)하거나 복원하세요."
      />
      <div style={{ maxWidth: 360, marginBottom: 18 }}>
        <Field
          placeholder="제목 검색"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
      </div>
      {error && <div style={{ color: T.danger, marginBottom: 12 }}>{error}</div>}

      <Card style={{ padding: 0, overflow: 'hidden' }}>
        {books.length === 0 && <div style={{ padding: 24, color: T.muted }}>책이 없습니다.</div>}
        {books.map((b, i) => (
          <div
            key={b.id}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 14,
              padding: '15px 20px',
              borderBottom: i < books.length - 1 ? `1px solid ${T.borderSoft}` : 'none',
              background: b.blocked ? '#fdf6f4' : 'transparent',
            }}
          >
            <Cover title={b.id} width={38} radius={6} label={false} style={{ opacity: b.blocked ? 0.5 : 1 }} />
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontSize: 14, fontWeight: 700, color: T.textStrong }}>{b.title}</div>
              <div style={{ fontSize: 12, color: T.muted, marginTop: 2 }}>
                {STATUS_LABEL[b.status] || b.status}
              </div>
            </div>
            {b.blocked ? (
              <>
                <Badge tone="danger">차단됨</Badge>
                <Button onClick={() => restore(b.id)}>복원</Button>
              </>
            ) : (
              <Button kind="danger" onClick={() => takedown(b.id)}>
                강제 비공개
              </Button>
            )}
          </div>
        ))}
      </Card>
    </div>
  );
}
