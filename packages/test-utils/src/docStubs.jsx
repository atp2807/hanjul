// DocReader/DocEditor 스텁 — web/src/pages/DocPage.test.jsx:9-17 의 실제 vi.mock('@hanjul/doc', ...)
// 블록에서 그대로 뽑아온 계약을 보존한다:
//   - DocReader: data-testid="doc-reader" 로 html prop 을 그대로 렌더.
//   - DocEditor: data-testid="doc-editor" 로 html 을 노출하고, "발화-저장" 버튼 클릭 시
//     onSave('<article data-juldoc="1">편집됨</article>') 를 호출.
//
// ⚠️ vi.mock 호이스팅 제약(authFixture.js 상단 경고와 동일): 테스트 파일에서
// `vi.mock('@hanjul/doc', () => docStubs())` 형태로 직접 호출해야 한다. 감싸는 헬퍼를
// 만들지 말 것 — 호이스팅은 테스트 파일 리터럴에만 적용된다.
export function docStubs() {
  return {
    DocReader: ({ html }) => <div data-testid="doc-reader">{html}</div>,
    DocEditor: ({ html, onSave }) => (
      <div data-testid="doc-editor">
        <button onClick={() => onSave('<article data-juldoc="1">편집됨</article>')}>발화-저장</button>
        <span>{html}</span>
      </div>
    ),
  };
}
