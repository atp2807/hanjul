import { useState } from 'react';

// 첫 출판 가이드 — 처음 글쓰기 화면에 3단계 안내. 닫으면 다신 안 뜸(localStorage).
const KEY = 'hanjul-writer-onboarded';

export function OnboardingTips() {
  const [show, setShow] = useState(() => !localStorage.getItem(KEY));
  if (!show) return null;

  const dismiss = () => {
    localStorage.setItem(KEY, '1');
    setShow(false);
  };

  return (
    <div
      data-testid="onboarding"
      style={{ border: '1px solid #e5e7eb', background: '#f9fafb', borderRadius: 12, padding: 16, marginBottom: 14 }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
        <strong style={{ fontSize: 15 }}>처음이세요? 3단계면 출판까지 끝나요</strong>
        <button onClick={dismiss} style={{ border: '1px solid #ddd', background: '#fff', borderRadius: 8, padding: '6px 12px', fontWeight: 600, cursor: 'pointer' }}>
          시작하기
        </button>
      </div>
      <ol style={{ margin: 0, paddingLeft: 20, color: '#555', fontSize: 14, lineHeight: 1.7 }}>
        <li><b>쓰기</b> — 그냥 쓰면 이 기기에 자동 저장돼요(오프라인·새로고침에도 안전). 제목은 <code>#&nbsp;</code> 또는 ‘제목’ 버튼.</li>
        <li><b>미리보기</b> — ‘미리보기’로 독자가 볼 모습을 확인.</li>
        <li><b>출판</b> — ‘출판’ 한 번이면 스토어에 올라가요. 표지·가격은 ‘책 정보 설정’에서.</li>
      </ol>
    </div>
  );
}
