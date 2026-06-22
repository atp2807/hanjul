// 로컬우선 글쓰기 페이지 (스파이크/Phase 0). 타이핑 → 즉시 로컬 저장(안 날아감).
// 동기화·원클릭 출판 연결은 다음 증분. 지금은 "빠르고 안 날아가는" 핵심만.
import { useParams } from 'react-router-dom';

import { WriterEditor } from '../writer/editor/WriterEditor';

export function WritePage() {
  const { id } = useParams();
  return (
    <div style={{ maxWidth: 760, margin: '0 auto', padding: '28px 24px' }}>
      <p style={{ color: '#aaa', fontSize: 13, margin: '0 0 12px' }}>
        로컬우선 에디터 · 입력 즉시 이 브라우저에 저장됨(오프라인·새로고침 생존)
      </p>
      <WriterEditor docId={id} />
    </div>
  );
}
