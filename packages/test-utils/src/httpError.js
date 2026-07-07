// packages/lib/src/apiClient.js:25-27 의 toError() 가 만드는 실제 에러 모양을 재현한다:
//   const err = new Error(detail || `API ${res.status}: ${path}`);
//   err.status = res.status;
//   err.detail = detail;
// 컴포넌트가 err.status/err.detail 을 보고 분기하는 에러 처리(404 안내문구, 서버 detail 노출 등)를
// mockApiClient().get.mockRejectedValue(httpError(404)) 형태로 검증할 때 쓴다.

/**
 * @param {number} status
 * @param {string|null} [detail=null]
 * @returns {Error & { status: number, detail: string|null }}
 */
export function httpError(status, detail = null) {
  const err = new Error(detail || `API ${status}`);
  err.status = status;
  err.detail = detail;
  return err;
}
