import { useState } from 'react';

import { api } from '../api';
import { T } from '../theme';
import { Badge, Button, Card, Field, Icon, PageHeader } from '../ui.jsx';

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
      <PageHeader title="회원·작가 관리" subtitle="계정을 조회하고 정지·서평단 자격을 조치하세요." />

      <Card style={{ marginBottom: 16 }}>
        <form onSubmit={lookup} style={{ display: 'flex', gap: 10, alignItems: 'flex-end' }}>
          <div style={{ flex: 1 }}>
            <Field
              label="계정 ID (UUID)"
              value={id}
              onChange={(e) => setId(e.target.value)}
              placeholder="00000000-0000-..."
            />
          </div>
          <Button kind="primary" type="submit" style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
            <Icon name="search" size={16} color="#eafaf5" />
            조회
          </Button>
        </form>
        {error && <div style={{ color: T.danger, marginTop: 10 }}>{error}</div>}
      </Card>

      {acc && (
        <Card>
          <div style={{ display: 'flex', alignItems: 'center', gap: 13, marginBottom: 16 }}>
            <span
              style={{
                width: 46,
                height: 46,
                borderRadius: 999,
                background: 'linear-gradient(140deg,#1d7e8e,#2aa0a8)',
                flexShrink: 0,
              }}
            />
            <div style={{ flex: 1 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 9 }}>
                <strong style={{ color: T.textStrong, fontSize: 17 }}>
                  {acc.displayName || '(이름 없음)'}
                </strong>
                <Badge tone={acc.statusCd === 'SUSPENDED' ? 'danger' : 'ok'}>
                  {acc.statusCd === 'SUSPENDED' ? '정지됨' : '정상'}
                </Badge>
                {acc.reviewBlocked && <Badge tone="warn">서평단 차단</Badge>}
              </div>
              <div style={{ fontSize: 13, color: T.muted, marginTop: 4 }}>
                {acc.email} · {acc.roleCd}
              </div>
            </div>
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            {acc.statusCd === 'SUSPENDED' ? (
              <Button onClick={() => act(() => api.unsuspend(acc.id))}>정지 해제</Button>
            ) : (
              <Button
                kind="danger"
                onClick={() => act(() => api.suspend(acc.id, window.prompt('정지 사유 (선택)') || null))}
              >
                계정 정지
              </Button>
            )}
            {acc.reviewBlocked ? (
              <Button onClick={() => act(() => api.unblockReview(acc.id))}>서평단 차단 해제</Button>
            ) : (
              <Button
                onClick={() => act(() => api.blockReview(acc.id, window.prompt('자격회수 사유 (선택)') || null))}
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
