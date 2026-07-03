import { T } from './theme';

/**
 * 조회 실패 인라인 안내 — 침묵 대신 사용자에게 알리고 재시도 버튼 제공.
 * @param {object} props
 * @param {string} [props.message='불러오기에 실패했어요.'] 사용자용 문구 (기술 메시지 금지)
 * @param {() => void} [props.onRetry] 있으면 "다시 시도" 버튼 노출
 * @param {import('react').CSSProperties} [props.style]
 */
export function ErrorNotice({ message = '불러오기에 실패했어요.', onRetry, style }) {
  return (
    <div
      role="alert"
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 12,
        padding: '13px 16px',
        background: T.dangerBg,
        color: T.danger,
        borderRadius: T.radius.lg,
        fontSize: 13.5,
        fontWeight: 600,
        fontFamily: T.font,
        ...style,
      }}
    >
      <span style={{ flex: 1 }}>{message}</span>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          style={{
            padding: '7px 14px',
            background: T.surface,
            color: T.danger,
            border: `1px solid ${T.danger}`,
            borderRadius: T.radius.sm,
            fontSize: 12.5,
            fontWeight: 700,
            cursor: 'pointer',
            fontFamily: T.font,
          }}
        >
          다시 시도
        </button>
      )}
    </div>
  );
}
