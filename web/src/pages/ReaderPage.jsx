import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';

import { Reader } from '../reader/Reader';
import { flattenBlocks, getBookContent } from '../services/api/books';

export function ReaderPage() {
  const { id } = useParams();
  const [blocks, setBlocks] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    getBookContent(id)
      .then((content) => setBlocks(flattenBlocks(content)))
      .catch((e) => setError(e.message));
  }, [id]);

  return (
    <div style={{ maxWidth: 680, margin: '24px auto', padding: '0 16px' }}>
      {error && <p style={{ color: 'crimson' }}>불러오기 실패: {error}</p>}
      {!blocks && !error && <p style={{ color: '#999' }}>불러오는 중…</p>}
      {blocks && <Reader blocks={blocks} />}
    </div>
  );
}
