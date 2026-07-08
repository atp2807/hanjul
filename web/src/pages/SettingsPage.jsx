import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';

import { useAuth } from '../auth/AuthContext';
import { exportMyData, withdraw } from '../services/api/auth';
import { Icon } from '../components/Icon';
import { T } from '../theme';

const QUICK_LINKS = [
  ['/library', 'read', '내 서재'],
  ['/settlement', null, '정산·출금'],
  ['/notifications', 'bell', '알림'],
  ['/studio', 'edit', '작가 스튜디오'],
];

function Section({ title, desc, children }) {
  return (
    <div style={{ background: T.surface, borderRadius: 16, padding: '24px 26px', marginBottom: 16 }}>
      <div style={{ fontSize: 16, fontWeight: 800, color: T.ink }}>{title}</div>
      {desc && <p style={{ fontSize: 13.5, color: T.muted, lineHeight: 1.6, margin: '8px 0 16px' }}>{desc}</p>}
      {children}
    </div>
  );
}

export function SettingsPage() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  if (!user) {
    return (
      <div style={{ padding: '54px 24px', textAlign: 'center', color: T.muted }}>
        로그인이 필요해요.{' '}
        <span onClick={() => navigate('/login')} style={{ color: T.ink, cursor: 'pointer', fontWeight: 600 }}>
          로그인
        </span>
      </div>
    );
  }

  async function download() {
    setError('');
    try {
      const data = await exportMyData();
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'hanjul-내정보.json';
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch {
      setError('내려받기에 실패했어요.');
    }
  }

  async function doWithdraw() {
    setError('');
    setBusy(true);
    try {
      await withdraw();
      logout();
      navigate('/', { replace: true });
    } catch {
      setError('탈퇴 처리에 실패했어요. 잠시 후 다시 시도해 주세요.');
      setBusy(false);
    }
  }

  return (
    <div style={{ padding: '40px 24px 80px' }}>
      <div style={{ maxWidth: 640, margin: '0 auto' }}>
        <h1 style={{ margin: '0 0 24px', fontSize: 26, fontWeight: 800, color: T.ink, letterSpacing: '-0.02em' }}>
          계정 설정
        </h1>

        <Section title="내 계정">
          <div style={{ fontSize: 14, color: T.textMid }}>
            {user.displayName || '-'} · {user.email}
          </div>
        </Section>

        <Section title="바로가기">
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10 }}>
            {QUICK_LINKS.map(([to, icon, label]) => (
              <Link
                key={to}
                to={to}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 6,
                  padding: '10px 16px',
                  borderRadius: T.radius.md,
                  border: `1px solid ${T.border}`,
                  background: T.bg,
                  color: T.textStrong,
                  fontSize: 13.5,
                  fontWeight: 600,
                  textDecoration: 'none',
                }}
              >
                {icon && <Icon name={icon} size={15} stroke={T.textMid} />}
                {label}
              </Link>
            ))}
          </div>
        </Section>

        <Section
          title="내 정보 내려받기"
          desc="회원님의 계정 정보를 JSON 파일로 내려받을 수 있어요."
        >
          <button
            onClick={download}
            style={{
              padding: '10px 18px',
              borderRadius: T.radius.md,
              border: `1px solid ${T.border}`,
              background: T.surface,
              color: T.textStrong,
              fontSize: 14,
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            내 정보 내려받기
          </button>
        </Section>

        <Section
          title="회원 탈퇴"
          desc="탈퇴하면 개인정보가 삭제되며, 소셜 로그인 연결도 해제됩니다. 단 관련 법령에 따라 구매·정산 등 거래 기록은 익명 처리되어 일정 기간(전자상거래법상 최대 5년) 보관됩니다. 탈퇴 후에는 계정을 복구할 수 없어요."
        >
          {error && <div style={{ color: '#c63c23', fontSize: 13, marginBottom: 12 }}>{error}</div>}
          {!confirming ? (
            <button
              onClick={() => setConfirming(true)}
              style={{
                padding: '10px 18px',
                borderRadius: T.radius.md,
                border: '1px solid #f3d3cb',
                background: '#fdeeea',
                color: '#c63c23',
                fontSize: 14,
                fontWeight: 700,
                cursor: 'pointer',
              }}
            >
              회원 탈퇴
            </button>
          ) : (
            <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
              <span style={{ fontSize: 14, color: T.textStrong, fontWeight: 600 }}>정말 탈퇴하시겠어요?</span>
              <button
                onClick={doWithdraw}
                disabled={busy}
                style={{
                  padding: '10px 18px',
                  borderRadius: T.radius.md,
                  border: 'none',
                  background: '#c63c23',
                  color: '#fff',
                  fontSize: 14,
                  fontWeight: 700,
                  cursor: 'pointer',
                }}
              >
                {busy ? '처리 중…' : '네, 탈퇴할게요'}
              </button>
              <button
                onClick={() => setConfirming(false)}
                disabled={busy}
                style={{
                  padding: '10px 18px',
                  borderRadius: T.radius.md,
                  border: `1px solid ${T.border}`,
                  background: T.surface,
                  color: T.textMid,
                  fontSize: 14,
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                취소
              </button>
            </div>
          )}
        </Section>
      </div>
    </div>
  );
}
