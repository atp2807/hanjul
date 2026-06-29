import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { api } from '../api';
import { useOps } from '../auth.jsx';
import { T } from '../theme';
import { Button, Field } from '../ui.jsx';

export default function Login() {
  const { login } = useOps();
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setError('');
    setBusy(true);
    try {
      const { token } = await api.login(email, password);
      login(token);
      navigate('/', { replace: true });
    } catch (err) {
      setError(err.status === 401 ? '이메일 또는 비밀번호가 올바르지 않습니다.' : '로그인 실패');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div style={{ display: 'grid', placeItems: 'center', minHeight: '100vh', padding: 20, background: T.sidebar }}>
      <div
        style={{
          width: 380,
          background: T.surface,
          borderRadius: 22,
          padding: '34px 32px',
          boxShadow: '0 30px 60px -28px rgba(0,0,0,0.5)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 9, marginBottom: 6 }}>
          <span style={{ width: 26, height: 26, borderRadius: 8, background: T.accent }} />
          <span style={{ fontSize: 20, fontWeight: 800, color: T.ink }}>한줄</span>
          <span
            style={{
              padding: '2px 8px',
              background: '#eef6f3',
              color: T.text,
              borderRadius: 6,
              fontSize: 10,
              fontWeight: 800,
              letterSpacing: '0.06em',
            }}
          >
            운영
          </span>
        </div>
        <div style={{ fontSize: 13, color: T.muted, marginBottom: 24 }}>운영자 콘솔에 로그인하세요.</div>
        <form onSubmit={submit}>
          <div style={{ marginBottom: 14 }}>
            <Field label="이메일" type="email" value={email} onChange={(e) => setEmail(e.target.value)} autoFocus />
          </div>
          <div style={{ marginBottom: 16 }}>
            <Field
              label="비밀번호"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>
          {error && <div style={{ color: T.danger, fontSize: 13, marginBottom: 14 }}>{error}</div>}
          <Button kind="primary" type="submit" disabled={busy} style={{ width: '100%', padding: '12px' }}>
            {busy ? '확인 중…' : '로그인'}
          </Button>
        </form>
      </div>
    </div>
  );
}
