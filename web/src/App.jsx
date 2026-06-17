import { useEffect, useState } from 'react';

import { Reader } from './reader/Reader';
import { flattenBlocks, getBookContent } from './services/api/books';
import { SAMPLE_BLOCKS } from './sampleBook';

// ?bookId=<uuid> 가 있으면 백엔드에서 정본을 불러오고, 없으면 샘플로 단독 데모.
export default function App() {
  const [blocks, setBlocks] = useState(SAMPLE_BLOCKS);
  const [error, setError] = useState(null);

  useEffect(() => {
    const bookId = new URLSearchParams(window.location.search).get('bookId');
    if (!bookId) return;
    getBookContent(bookId)
      .then((content) => setBlocks(flattenBlocks(content)))
      .catch((e) => setError(e.message));
  }, []);

  return (
    <div style={{ maxWidth: 640, margin: '40px auto', padding: '0 16px' }}>
      <h2 style={{ fontWeight: 600 }}>한줄 리더 — Pretext 조판 데모</h2>
      {error && <p style={{ color: 'crimson' }}>불러오기 실패: {error} (샘플로 표시)</p>}
      <Reader blocks={blocks} />
    </div>
  );
}
