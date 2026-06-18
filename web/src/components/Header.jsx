import { Link } from 'react-router-dom';

export function Header() {
  return (
    <header
      style={{
        borderBottom: '1px solid #eee',
        padding: '14px 24px',
        display: 'flex',
        alignItems: 'baseline',
        gap: 16,
        position: 'sticky',
        top: 0,
        background: '#fff',
        zIndex: 10,
      }}
    >
      <Link to="/" style={{ textDecoration: 'none', color: '#111' }}>
        <strong style={{ fontSize: 22, letterSpacing: '-0.02em' }}>한줄</strong>
      </Link>
      <span style={{ color: '#999', fontSize: 13 }}>글로벌 ebook 출판</span>
    </header>
  );
}
