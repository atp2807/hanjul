import { Link } from 'react-router-dom';

import { BUSINESS as B } from '../config/business';
import { DOCS, DOC_ORDER } from '../legal/documents';
import { T } from '../theme';

// 전자상거래법 §10 사업자정보 표시 + 법률문서 링크. 몰입화면(리더·에디터) 제외하고 노출.
export function Footer() {
  const year = new Date().getFullYear();
  return (
    <footer
      style={{
        borderTop: `1px solid ${T.border}`,
        background: T.surface,
        padding: '30px 24px 44px',
        marginTop: 48,
      }}
    >
      <div style={{ maxWidth: 1080, margin: '0 auto' }}>
        <nav style={{ display: 'flex', flexWrap: 'wrap', gap: '10px 20px', marginBottom: 18 }}>
          {DOC_ORDER.map((slug) => (
            <Link
              key={slug}
              to={`/legal/${slug}`}
              style={{
                fontSize: 13,
                color: T.textMid,
                textDecoration: 'none',
                fontWeight: slug === 'privacy' ? 700 : 600,
              }}
            >
              {DOCS[slug].title}
            </Link>
          ))}
        </nav>
        <div style={{ fontSize: 12, color: T.muted, lineHeight: 1.9 }}>
          <div style={{ fontWeight: 600, color: T.textMid }}>
            {B.service} · {B.company}
          </div>
          <div>
            대표 {B.ceo} · 사업자등록번호 {B.bizNo} · 통신판매업신고 {B.mailOrderNo}
          </div>
          <div>
            {B.address} · {B.tel} · {B.email}
          </div>
          <div>
            출판사신고 {B.publisherNo} · 호스팅 제공: {B.host}
          </div>
          <div style={{ marginTop: 8 }}>© {year} {B.company}. All rights reserved.</div>
        </div>
      </div>
    </footer>
  );
}
