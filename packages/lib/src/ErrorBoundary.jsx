import { Component } from 'react';

// 최상위 렌더 에러 경계 — 컴포넌트 트리에서 던져진 예외를 잡아 앱 전체 백화면을 막는다.
// self-styling(인라인) · 외부 의존 없음 → 어느 앱에서도 최상위에 그대로 감싼다.
const WRAP = {
  minHeight: '100vh',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  padding: 24,
  background: '#f3faf8',
  fontFamily: "'IBM Plex Sans KR', -apple-system, BlinkMacSystemFont, system-ui, sans-serif",
};
const CARD = {
  maxWidth: 420,
  width: '100%',
  background: '#ffffff',
  borderRadius: 18,
  padding: '36px 32px',
  textAlign: 'center',
  boxShadow: '0 24px 48px -20px rgba(12,58,50,0.22)',
};
const BTN = {
  padding: '11px 20px',
  border: 'none',
  borderRadius: 10,
  background: '#0e4a5c',
  color: '#eafaf5',
  fontSize: 14,
  fontWeight: 700,
  cursor: 'pointer',
};

/**
 * 렌더 에러 경계. 자식 트리에서 예외가 던져지면 폴백 UI를 보여준다.
 * @param {object} props
 * @param {string} [props.home='/'] "홈으로" 목적지
 * @param {string} [props.title='문제가 발생했어요'] 폴백 제목
 * @param {import('react').ReactNode} [props.children]
 */
export class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error, info) {
    // 중앙 로깅 지점 — 추후 원격 리포팅(Sentry 등) 연결 자리.
    console.error('[ErrorBoundary]', error, info?.componentStack);
  }

  render() {
    if (!this.state.hasError) return this.props.children;
    const home = this.props.home ?? '/';
    return (
      <div style={WRAP}>
        <div style={CARD}>
          <div style={{ fontSize: 18, fontWeight: 800, color: '#0e4a5c', letterSpacing: '-0.02em' }}>
            {this.props.title ?? '문제가 발생했어요'}
          </div>
          <p style={{ fontSize: 14, color: '#52615b', lineHeight: 1.6, margin: '12px 0 24px' }}>
            일시적인 오류가 났어요. 새로고침하면 대부분 해결돼요. 계속되면 잠시 후 다시 시도해주세요.
          </p>
          <div style={{ display: 'flex', gap: 10, justifyContent: 'center' }}>
            <button type="button" style={BTN} onClick={() => window.location.reload()}>
              새로고침
            </button>
            <button
              type="button"
              style={{ ...BTN, background: 'transparent', color: '#0e4a5c', border: '1px solid #e3efea' }}
              onClick={() => { window.location.href = home; }}
            >
              홈으로
            </button>
          </div>
        </div>
      </div>
    );
  }
}
