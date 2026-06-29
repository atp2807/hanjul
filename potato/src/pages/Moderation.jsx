import { useCallback, useEffect, useState } from 'react';

import { api } from '../api';
import { T } from '../theme';
import { Badge, Button, Card } from '../ui.jsx';

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
    const reason = window.prompt('비공개 사유 (감사 로그에 기록됩니다)');
    if (reason === null) return;
    await api.takedown(id, reason);
    load();
  }

  async function restore(id) {
    await api.restore(id);
    load();
  }

  return (
    <div>
      <h1 style={{ fontSize: 22, color: T.textStrong, marginTop: 0 }}>모더레이션</h1>
      <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
        <input
          placeholder="제목 검색"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          style={{
            font: T.font,
            fontSize: 14,
            padding: '8px 12px',
            borderRadius: T.radius.md,
            border: `1px solid ${T.border}`,
            flex: 1,
          }}
        />
      </div>
      {error && <div style={{ color: T.danger, marginBottom: 12 }}>{error}</div>}
      <Card style={{ padding: 0 }}>
        {books.length === 0 && (
          <div style={{ padding: 20, color: T.muted }}>책이 없습니다.</div>
        )}
        {books.map((b) => (
          <div
            key={b.id}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 12,
              padding: '14px 18px',
              borderBottom: `1px solid ${T.borderSoft}`,
            }}
          >
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 600, color: T.textStrong }}>{b.title}</div>
              <div style={{ fontSize: 12, color: T.muted }}>{b.status}</div>
            </div>
            {b.blocked ? (
              <>
                <Badge tone="danger">차단됨</Badge>
                <Button kind="ghost" onClick={() => restore(b.id)}>
                  복원
                </Button>
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
