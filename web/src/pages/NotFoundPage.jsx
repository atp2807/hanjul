import { Link } from 'react-router-dom';

import { T } from '../theme';

export function NotFoundPage() {
  return (
    <div style={{ display: 'grid', placeItems: 'center', minHeight: '60vh', padding: 24, textAlign: 'center' }}>
      <div>
        <div style={{ fontSize: 48, fontWeight: 800, color: T.ink, letterSpacing: '-0.03em' }}>404</div>
        <p style={{ fontSize: 15, color: T.muted, margin: '10px 0 22px' }}>
          찾는 페이지가 없어요. 주소가 바뀌었거나 삭제됐을 수 있어요.
        </p>
        <Link
          to="/"
          style={{
            display: 'inline-block',
            padding: '11px 22px',
            background: T.ink,
            color: T.inkText,
            borderRadius: T.radius.pill,
            fontSize: 14,
            fontWeight: 600,
            textDecoration: 'none',
          }}
        >
          서점으로 가기
        </Link>
      </div>
    </div>
  );
}
