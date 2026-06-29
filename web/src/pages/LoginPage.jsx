import { useState } from 'react';

import { BrandMark } from '../components/BrandMark';
import { getLoginUrl } from '../services/api/auth';
import { T } from '../theme';

// 한줄 로그인 — 시안(로그인 화면) 반영. 인증은 Google OAuth(리다이렉트).
// 이메일/비번·카카오는 미지원이라 가짜 입력칸 대신 소셜 CTA만 정직하게.
export function LoginPage() {
  const [busy, setBusy] = useState(false);

  async function google() {
    setBusy(true);
    try {
      const { authorizationUrl } = await getLoginUrl('google');
      window.location.href = authorizationUrl;
    } catch {
      setBusy(false);
    }
  }

  return (
    <div style={{ maxWidth: 1080, margin: '32px auto', padding: '0 24px' }}>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', borderRadius: 24, overflow: 'hidden', boxShadow: T.shadow, background: T.surface }}>
        {/* 브랜드 패널 */}
        <div style={{ background: `linear-gradient(150deg, ${T.heroFrom}, oklch(0.72 0.11 204))`, padding: '56px', position: 'relative', overflow: 'hidden', display: 'flex', flexDirection: 'column', minHeight: 460 }}>
          <div style={{ position: 'absolute', right: -90, top: -90, width: 300, height: 300, borderRadius: 999, background: 'rgba(255,255,255,0.15)' }} />
          <div style={{ position: 'absolute', left: -60, bottom: -100, width: 240, height: 240, borderRadius: 999, background: 'rgba(255,255,255,0.1)' }} />
          <div style={{ display: 'flex', alignItems: 'center', gap: 9, position: 'relative' }}>
            <BrandMark size={28} />
            <span style={{ fontSize: 22, fontWeight: 800, color: '#06342c' }}>한줄</span>
          </div>
          <div style={{ marginTop: 'auto', position: 'relative' }}>
            <div style={{ fontSize: 34, fontWeight: 800, lineHeight: 1.3, color: '#06342c', letterSpacing: '-0.03em' }}>읽고, 쓰고,<br />펴내는 모든 순간.</div>
            <p style={{ margin: '18px 0 0', fontSize: 15, lineHeight: 1.7, color: '#0d4339', maxWidth: 340 }}>서점·에디터·출판을 하나로. 오늘 당신의 첫 문장을 시작하세요.</p>
          </div>
        </div>

        {/* 로그인 */}
        <div style={{ padding: '64px', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
          <h1 style={{ margin: '0 0 6px', fontSize: 26, fontWeight: 800, color: T.ink, letterSpacing: '-0.025em' }}>한줄 시작하기</h1>
          <div style={{ fontSize: 14, color: T.muted, marginBottom: 28 }}>소셜 계정으로 바로 시작하세요.</div>

          <button
            onClick={google}
            disabled={busy}
            style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10, padding: 15, background: T.ink, color: T.inkText, border: 'none', borderRadius: 13, fontSize: 15, fontWeight: 700, cursor: 'pointer' }}
          >
            {busy ? '이동 중…' : 'Google로 계속하기'}
          </button>

          <div style={{ textAlign: 'center', fontSize: 13, color: T.muted, marginTop: 24, lineHeight: 1.6 }}>
            가입 즉시 독자로 시작해요. <br />책을 만들면 자동으로 작가가 됩니다.
          </div>
        </div>
      </div>
    </div>
  );
}
