import { T } from '../theme';
import { Icon } from './Icon';

// 빈 상태 공용 — 아이콘 + 제목 + 설명 + 선택 액션. 화면마다 복붙하지 말고 이걸 사용.
// <EmptyState icon="search" title="..." desc="..." action={{ label, onClick }} />
export function EmptyState({ icon, title, desc, action }) {
  return (
    <div style={{ textAlign: 'center', padding: '56px 16px', background: T.surface, borderRadius: 16, border: `1px solid ${T.borderSoft}` }}>
      {icon && (
        <div style={{ width: 52, height: 52, borderRadius: 15, background: '#e9f7f1', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 14px' }}>
          <Icon name={icon} size={24} stroke="#297961" />
        </div>
      )}
      <div style={{ fontSize: 15, fontWeight: 700, color: T.textStrong }}>{title}</div>
      {desc && <div style={{ fontSize: 13, color: T.muted, marginTop: 6, lineHeight: 1.6 }}>{desc}</div>}
      {action && (
        <button
          onClick={action.onClick}
          style={{ marginTop: 14, padding: '9px 18px', background: T.ink, color: T.inkText, border: 'none', borderRadius: 10, fontSize: 12.5, fontWeight: 700, cursor: 'pointer' }}
        >
          {action.label}
        </button>
      )}
    </div>
  );
}
