import { Link, useParams } from 'react-router-dom';

import { DOCS } from '../legal/documents';
import { T } from '../theme';

export function LegalPage() {
  const { slug } = useParams();
  const doc = DOCS[slug];

  if (!doc) {
    return (
      <div style={{ padding: '54px 24px', textAlign: 'center', color: T.muted }}>
        문서를 찾을 수 없습니다. <Link to="/" style={{ color: T.ink }}>홈으로</Link>
      </div>
    );
  }

  return (
    <div style={{ padding: '48px 24px 80px' }}>
      <div style={{ maxWidth: 760, margin: '0 auto' }}>
        <h1 style={{ margin: '0 0 6px', fontSize: 28, fontWeight: 800, color: T.ink, letterSpacing: '-0.02em' }}>
          {doc.title}
        </h1>
        <div style={{ fontSize: 13, color: T.muted, marginBottom: 10 }}>최종 개정 {doc.updated}</div>
        {/* ⚠️ 검수 완료 후 이 배너 제거 */}
        <div
          style={{
            background: '#fff8e6',
            border: '1px solid #f0e2bd',
            borderRadius: 10,
            padding: '10px 14px',
            fontSize: 12.5,
            color: '#8a6712',
            marginBottom: 30,
          }}
        >
          본 문서는 초안입니다. 법률 검토 후 확정됩니다.
        </div>
        {doc.sections.map((s, i) => (
          <section key={i} style={{ marginBottom: 22 }}>
            <h2 style={{ fontSize: 16, fontWeight: 700, color: T.textStrong, margin: '0 0 8px' }}>{s.h}</h2>
            {s.p.map((para, j) => (
              <p key={j} style={{ fontSize: 14, lineHeight: 1.85, color: T.textMid, margin: '0 0 6px' }}>
                {para}
              </p>
            ))}
          </section>
        ))}
      </div>
    </div>
  );
}
