import { useState } from 'react';

import { api } from '../api';
import { T } from '../theme';
import { Badge, Button, Card, Field } from '../ui.jsx';

export default function Accounts() {
  const [id, setId] = useState('');
  const [acc, setAcc] = useState(null);
  const [error, setError] = useState('');

  async function lookup(e) {
    e?.preventDefault();
    setError('');
    setAcc(null);
    try {
      setAcc(await api.account(id.trim()));
    } catch (err) {
      setError(err.status === 404 ? '계정을 찾을 수 없습니다.' : '조회 실패');
    }
  }

  async function act(fn) {
    await fn();
    lookup();
  }

  return (
    <div>
      <h1 style={{ fontSize: 22, color: T.textStrong, marginTop: 0 }}>계정 조치</h1>
      <Card style={{ marginBottom: 16 }}>
        <form onSubmit={lookup} style={{ display: 'flex', gap: 8, alignItems: 'flex-end' }}>
          <div style={{ flex: 1 }}>
            <Field
              label="계정 ID (UUID)"
              value={id}
              onChange={(e) => setId(e.target.value)}
              placeholder="00000000-0000-..."
              style={{ marginBottom: 0 }}
            />
          </div>
          <Button kind="primary" type="submit">
            조회
          </Button>
        </form>
        {error && <div style={{ color: T.danger, marginTop: 10 }}>{error}</div>}
      </Card>

      {acc && (
        <Card>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
            <strong style={{ color: T.textStrong, fontSize: 16 }}>
              {acc.displayName || '(이름 없음)'}
            </strong>
            <Badge tone={acc.statusCd === 'SUSPENDED' ? 'danger' : 'ok'}>{acc.statusCd}</Badge>
            {acc.reviewBlocked && <Badge tone="warn">서평단 차단</Badge>}
          </div>
          <div style={{ fontSize: 13, color: T.muted, marginBottom: 16 }}>
            {acc.email} · {acc.roleCd}
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            {acc.statusCd === 'SUSPENDED' ? (
              <Button onClick={() => act(() => api.unsuspend(acc.id))}>정지 해제</Button>
            ) : (
              <Button
                kind="danger"
                onClick={() =>
                  act(() => api.suspend(acc.id, window.prompt('정지 사유 (선택)') || null))
                }
              >
                계정 정지
              </Button>
            )}
            {acc.reviewBlocked ? (
              <Button onClick={() => act(() => api.unblockReview(acc.id))}>서평단 차단 해제</Button>
            ) : (
              <Button
                kind="ghost"
                onClick={() =>
                  act(() => api.blockReview(acc.id, window.prompt('자격회수 사유 (선택)') || null))
                }
              >
                서평단 자격회수
              </Button>
            )}
          </div>
        </Card>
      )}
    </div>
  );
}
