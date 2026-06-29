// 알림 종류별 표시 — 벨 드롭다운(NotificationBell)과 알림함(NotificationsPage) 공유.
// 새 종류 추가 시 여기 한 곳만 고치면 양쪽 반영.
export const KIND_LABEL = { NEW_BOOK: '신간', REVISION: '개정판', ASSIGNED: '서평단', DUE_SOON: '마감 임박' };
export const KIND_SUFFIX = {
  NEW_BOOK: '이(가) 출간됐어요.',
  REVISION: '의 개정판이 나왔어요.',
  ASSIGNED: ' 서평단에 배정됐어요. 증정본이 서재에 도착했어요.',
  DUE_SOON: ' 리뷰 마감이 다가와요. 잊지 말고 작성해 주세요.',
};
export const KIND_ICON = { NEW_BOOK: '🚀', REVISION: '✏️', ASSIGNED: '🎁', DUE_SOON: '⏰' };
export const KIND_ICON_BG = { NEW_BOOK: '#e3f3ec', REVISION: '#fff3da', ASSIGNED: '#e3f3ec', DUE_SOON: '#fdeeea' };
