import { useRef } from 'react';

import { useFocusTrap } from '../hooks/useFocusTrap';
import { Reader } from '../reader/Reader';

/**
 * 출판 전 미리보기 모달 — 독자가 볼 리더 모습(기존 Reader/Pretext 재사용).
 * 배경을 덮는 실제(blocking) 모달이라 4가지 키보드 접근성을 전부 적용:
 * 열릴 때 포커스 이동·Tab 트랩·Esc로 닫기·닫힐 때 트리거로 포커스 리턴(lr-ca34f579 ②).
 * @param {object} props
 * @param {Array} props.blocks 미리볼 블록(없으면 안내 문구)
 * @param {() => void} props.onClose 닫기 콜백(배경 클릭·닫기 버튼·Esc 공용)
 */
export function PreviewModal({ blocks, onClose }) {
  const dialogRef = useRef(null);
  useFocusTrap({ open: true, onClose, containerRef: dialogRef });

  return (
    <div
      data-testid="preview-overlay"
      onClick={onClose}
      style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,.5)', zIndex: 30, display: 'flex', alignItems: 'center', justifyContent: 'center' }}
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="preview-modal-title"
        data-testid="preview-body"
        onClick={(e) => e.stopPropagation()}
        style={{ background: '#fff', padding: 20, borderRadius: 12, maxHeight: '92vh', overflow: 'auto' }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10, gap: 16 }}>
          <strong id="preview-modal-title" data-testid="preview-title">출판 전 미리보기 (독자가 볼 모습)</strong>
          <button onClick={onClose} style={{ padding: '6px 12px', borderRadius: 8, border: '1px solid #ddd', cursor: 'pointer' }}>닫기</button>
        </div>
        {blocks.length ? <Reader blocks={blocks} /> : <p style={{ color: '#999' }}>아직 내용이 없어요.</p>}
      </div>
    </div>
  );
}
