import { useRef, useState } from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { useFocusTrap } from './useFocusTrap';

// 커스텀 모달/드롭다운 패널 4대 키보드 접근성(포커스 이동·Tab 트랩·Esc 닫기·포커스 리턴)의
// 순수 훅 단위 검증 — 실제 컴포넌트(NotificationBell/Reader TOC/PreviewModal)는 이 훅을 재사용.
function Harness({ onClose }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  useFocusTrap({
    open,
    onClose: () => {
      onClose?.();
      setOpen(false);
    },
    containerRef: ref,
  });
  return (
    <div>
      <button data-testid="trigger" onClick={() => setOpen(true)}>열기</button>
      {open && (
        <div ref={ref} data-testid="panel">
          <button data-testid="first">첫번째</button>
          <button data-testid="second">두번째</button>
        </div>
      )}
    </div>
  );
}

describe('useFocusTrap', () => {
  it('열리면 패널 안 첫 포커스 가능 요소로 이동', () => {
    render(<Harness />);
    fireEvent.click(screen.getByTestId('trigger'));
    expect(screen.getByTestId('first')).toHaveFocus();
  });

  it('마지막 요소에서 Tab → 처음으로 순환(트랩)', () => {
    render(<Harness />);
    fireEvent.click(screen.getByTestId('trigger'));
    screen.getByTestId('second').focus();
    fireEvent.keyDown(document, { key: 'Tab' });
    expect(screen.getByTestId('first')).toHaveFocus();
  });

  it('첫 요소에서 Shift+Tab → 마지막으로 순환(트랩)', () => {
    render(<Harness />);
    fireEvent.click(screen.getByTestId('trigger'));
    expect(screen.getByTestId('first')).toHaveFocus();
    fireEvent.keyDown(document, { key: 'Tab', shiftKey: true });
    expect(screen.getByTestId('second')).toHaveFocus();
  });

  it('Esc → onClose 호출 + 트리거로 포커스 리턴', () => {
    const onClose = vi.fn();
    render(<Harness onClose={onClose} />);
    // jsdom의 fireEvent.click은 실브라우저의 버튼 클릭-시-포커스 기본동작을 재현하지 않으므로
    // "열기 전 트리거에 포커스가 있었다"는 실제 상황을 명시적으로 재현.
    const trigger = screen.getByTestId('trigger');
    trigger.focus();
    fireEvent.click(trigger);
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(onClose).toHaveBeenCalledTimes(1);
    expect(trigger).toHaveFocus();
    expect(screen.queryByTestId('panel')).not.toBeInTheDocument();
  });
});
