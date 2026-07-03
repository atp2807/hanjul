import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import { useAuth } from '../auth/AuthContext';
import { getAuthor } from '../services/api/authors';
import { followAuthor, getFollowStatus, unfollowAuthor } from '../services/api/notifications';
import { coverGradient, T } from '../theme';
import { Cover } from '../components/ui';

export function AuthorPage() {
  const { id } = useParams();
  const { user } = useAuth();
  const [author, setAuthor] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    getAuthor(id).then(setAuthor).catch((e) => setError(e.status === 404 ? '작가를 찾을 수 없어요.' : e.message));
  }, [id]);

  if (error) return <Center>{error}</Center>;
  if (!author) return <Center>불러오는 중…</Center>;

  // 로그인했고 본인 페이지가 아닐 때만 팔로우 가능
  const canFollow = user && user.id !== author.id;

  return (
    <div>
      {/* 커버 배너 */}
      <div style={{ height: 170, background: `linear-gradient(120deg, ${T.heroFrom}, oklch(0.7 0.11 205))` }} />
      <div style={{ maxWidth: 1080, margin: '0 auto', padding: '0 40px 56px' }}>
        <div style={{ display: 'flex', alignItems: 'flex-end', gap: 24, marginTop: -52, position: 'relative', flexWrap: 'wrap' }}>
          <div style={{ width: 120, height: 120, borderRadius: 28, background: coverGradient(author.displayName || id), border: `4px solid ${T.bg}`, boxShadow: '0 10px 24px -10px rgba(12,58,50,0.4)', flexShrink: 0 }} />
          <div style={{ flex: 1, paddingBottom: 8, minWidth: 180 }}>
            <h1 data-testid="author-name" style={{ margin: 0, fontSize: 30, fontWeight: 800, color: T.ink, letterSpacing: '-0.025em' }}>{author.displayName || '작가'}</h1>
            {author.bio && <div style={{ fontSize: 14, color: T.muted, marginTop: 4 }}>{author.bio.split('\n')[0].slice(0, 60)}</div>}
          </div>
          {canFollow && <div style={{ paddingBottom: 8 }}><FollowButton authorId={author.id} /></div>}
        </div>

        <div style={{ display: 'flex', gap: 40, margin: '28px 0 0', padding: '20px 0', borderTop: `1px solid ${T.border}`, borderBottom: `1px solid ${T.border}` }}>
          <Stat n={author.books.length} label="작품" />
        </div>

        {author.bio && (
          <p data-testid="author-bio" style={{ margin: '26px 0 0', maxWidth: 680, fontSize: 15, lineHeight: 1.85, color: '#52615b', whiteSpace: 'pre-wrap' }}>{author.bio}</p>
        )}

        <h3 style={{ margin: '38px 0 18px', fontSize: 20, fontWeight: 800, color: T.ink, letterSpacing: '-0.02em' }}>작품</h3>
        {author.books.length === 0 && <p style={{ color: T.muted }}>아직 출판한 책이 없어요.</p>}
        <div data-testid="author-books" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(170px, 1fr))', gap: 22 }}>
          {author.books.map((b) => (
            <Link key={b.id} to={`/books/${b.id}`} style={{ textDecoration: 'none', color: 'inherit' }}>
              <Cover url={b.coverUrl} title={b.title} radius={12} />
              <div style={{ marginTop: 9, fontWeight: 700, fontSize: 15, color: T.textStrong }}>{b.title}</div>
              <div style={{ color: T.muted, fontSize: 13 }}>{b.priceAmt != null ? `${b.priceAmt.toLocaleString()}원` : '무료'}</div>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}

function Stat({ n, label }) {
  return (
    <div>
      <span style={{ fontSize: 20, fontWeight: 800, color: T.ink }}>{n}</span>{' '}
      <span style={{ fontSize: 14, color: T.muted }}>{label}</span>
    </div>
  );
}

function FollowButton({ authorId }) {
  const [following, setFollowing] = useState(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');

  useEffect(() => {
    // 상태 확인 실패 → 미팔로우로 표시하되, 토글 실패는 아래서 반드시 안내 (무반응 금지)
    getFollowStatus(authorId).then((s) => setFollowing(s.following)).catch(() => setFollowing(false));
  }, [authorId]);

  async function toggle() {
    if (busy || following === null) return;
    setBusy(true);
    setErr('');
    const next = !following;
    try {
      if (next) await followAuthor(authorId);
      else await unfollowAuthor(authorId);
      setFollowing(next);
    } catch (e) {
      setErr(e.detail || '처리에 실패했어요. 잠시 후 다시 시도해 주세요.');
    } finally {
      setBusy(false);
    }
  }

  if (following === null) return null;
  return (
    <>
      <button
        data-testid="follow-btn"
        onClick={toggle}
        disabled={busy}
        style={{
          padding: '12px 26px',
          borderRadius: 12,
          border: following ? `1px solid #d6e4de` : 'none',
          background: following ? T.surface : T.ink,
          color: following ? T.textMid : T.inkText,
          fontWeight: 700,
          fontSize: 14,
          cursor: 'pointer',
        }}
      >
        {following ? '팔로잉' : '＋ 팔로우'}
      </button>
      {err && <div role="alert" style={{ marginTop: 8, fontSize: 12.5, color: T.danger, fontWeight: 600 }}>{err}</div>}
    </>
  );
}

function Center({ children }) {
  return <p style={{ textAlign: 'center', color: T.muted, padding: 40 }}>{children}</p>;
}
