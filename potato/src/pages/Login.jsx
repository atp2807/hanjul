import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { api } from '../api';
import { useOps } from '../auth.jsx';
import { T } from '../theme';
import { Button, Card, Field } from '../ui.jsx';

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
    <div style={{ display: 'grid', placeItems: 'center', minHeight: '100vh', padding: 20 }}>
      <Card style={{ width: 360, boxShadow: T.shadow }}>
        <div style={{ fontSize: 24, fontWeight: 700, color: T.ink, marginBottom: 4 }}>potato</div>
        <div style={{ fontSize: 13, color: T.muted, marginBottom: 20 }}>한줄 운영자 콘솔</div>
        <form onSubmit={submit}>
          <Field
            label="이메일"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoFocus
          />
          <Field
            label="비밀번호"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          {error && (
            <div style={{ color: T.danger, fontSize: 13, marginBottom: 12 }}>{error}</div>
          )}
          <Button kind="primary" type="submit" disabled={busy} style={{ width: '100%' }}>
            {busy ? '확인 중…' : '로그인'}
          </Button>
        </form>
      </Card>
    </div>
  );
}
