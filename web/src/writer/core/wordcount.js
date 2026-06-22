// 글자수/진행도 — 작가 동기부여 (Track1-B). 순수.
// hr 등 비텍스트 블록 제외, 공백 포함 문자 수.

export function charCount(doc) {
  return (doc.blocks || []).reduce(
    (n, b) => n + (b.spans || []).reduce((m, s) => m + s.text.length, 0),
    0,
  );
}

// 공백 기준 단어 수 (영문 등). 한글은 보통 글자수를 보지만 보조 지표로 제공.
export function wordCount(doc) {
  const text = (doc.blocks || [])
    .flatMap((b) => (b.spans || []).map((s) => s.text))
    .join(' ')
    .trim();
  return text ? text.split(/\s+/).length : 0;
}
