import { useEffect, useRef } from 'react';

const FOCUSABLE_SELECTOR = [
  'a[href]',
  'button:not([disabled])',
  'textarea:not([disabled])',
  'input:not([disabled])',
  'select:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(',');

/**
 * 커스텀 모달/드롭다운 패널의 키보드 접근성 — 열릴 때 포커스 이동, Tab 트랩,
 * Esc로 닫기, 닫힐 때 트리거로 포커스 리턴 4가지를 한 번에 처리한다.
 * (WCAG 2.1.1 키보드, 2.4.3 포커스 순서, 2.1.2 트랩 없음 — 커스텀 위젯이라 브라우저가
 * 대신 해주지 않는 부분. lr-ca34f579 남은 항목 ②.)
 *
 * @param {object} opts
 * @param {boolean} opts.open 패널이 열려 있는지
 * @param {() => void} opts.onClose Esc(또는 트랩 설정에 따라) 닫을 때 호출
 * @param {import('react').RefObject<HTMLElement>} opts.containerRef 트랩 대상 컨테이너(패널 루트)
 * @param {boolean} [opts.trap=true] Tab을 컨테이너 안에 가둘지 — 전체화면 모달은 true,
 *   바깥 클릭으로도 자연스레 닫히는 비차단 드롭다운도 일관성을 위해 기본 true로 둔다.
 */
export function useFocusTrap({ open, onClose, containerRef, trap = true }) {
  const returnFocusRef = useRef(null);

  useEffect(() => {
    if (!open) return undefined;

    returnFocusRef.current = document.activeElement;
    const container = containerRef.current;

    function focusables() {
      return Array.from(container?.querySelectorAll(FOCUSABLE_SELECTOR) || []);
    }

    // 열리는 즉시 패널 안 첫 포커스 가능 요소로 이동(없으면 컨테이너 자체, 트랩 위해 tabIndex=-1 필요)
    const first = focusables()[0];
    if (first) first.focus();
    else if (container) { container.setAttribute('tabindex', '-1'); container.focus(); }

    function onKeyDown(e) {
      if (e.key === 'Escape') {
        e.stopPropagation();
        onClose();
        return;
      }
      if (!trap || e.key !== 'Tab') return;
      const els = focusables();
      if (els.length === 0) return;
      const firstEl = els[0];
      const lastEl = els[els.length - 1];
      if (e.shiftKey && document.activeElement === firstEl) {
        e.preventDefault();
        lastEl.focus();
      } else if (!e.shiftKey && document.activeElement === lastEl) {
        e.preventDefault();
        firstEl.focus();
      }
    }

    document.addEventListener('keydown', onKeyDown, true);
    return () => {
      document.removeEventListener('keydown', onKeyDown, true);
      returnFocusRef.current?.focus?.();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);
}
