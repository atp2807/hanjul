import { apiClient } from './api_client';

// 모집중 캠페인 목록 (서평단 피드) — category 지정 시 그 장르만
export function listOpenCampaigns(category) {
  return apiClient.get(`/campaigns/open${category ? `?category=${encodeURIComponent(category)}` : ''}`);
}
// 캠페인 상세 (공개)
export function getCampaign(id) {
  return apiClient.get(`/campaigns/${id}`);
}
// 리뷰어 신청
export function applyCampaign(id) {
  return apiClient.post(`/campaigns/${id}/apply`);
}
// 신청 취소 (배정 전)
export function cancelApplication(id) {
  return apiClient.del(`/campaigns/${id}/apply`);
}
// 내 신청 현황 (리뷰어)
export function getMyApplications() {
  return apiClient.get('/me/applications');
}
// 내 신뢰도·자격 (완료/미작성/완료율/자격회수)
export function getReviewerStatus() {
  return apiClient.get('/me/reviewer-status');
}
// 작가 — 캠페인 생성
export function createCampaign({ bookId, slots, reviewDays = 14, minChars = 0 }) {
  return apiClient.post('/campaigns', { bookId, slots, reviewDays, minChars });
}
// 작가 — 내 캠페인 + 집계 (관리 대시보드)
export function getMyCampaigns() {
  return apiClient.get('/me/campaigns');
}
// 작가 — 캠페인 신청자 목록 (배정용)
export function getApplicants(id) {
  return apiClient.get(`/campaigns/${id}/applications`);
}
// 작가 — 리뷰어 배정 (증정본 지급)
export function assignReviewer(id, applicantId) {
  return apiClient.post(`/campaigns/${id}/assign`, { applicantId });
}

// 마감일(ISO) → "D-2" / "마감" / "D-day"
export function dday(deadlineAt) {
  if (!deadlineAt) return null;
  const ms = new Date(deadlineAt).getTime() - Date.now();
  const d = Math.ceil(ms / 86400000);
  if (d < 0) return '마감';
  if (d === 0) return 'D-day';
  return `D-${d}`;
}
