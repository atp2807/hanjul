// 정본 블록 모델 — 백엔드 pub.block.block_type_cd 와 1:1.
// (backend engine/imports/text_to_blocks.py 의 P/H1/H2/H3/QUOTE/HR 미러)
//
// 세 표현을 오간다:
//   중립 type(소문자, 에디터/직렬화 내부)  ↔  정본 코드(대문자, DB/API)  ↔  HTML 태그
// 순수 모듈 — import 없음. 어디서나(웹·데스크톱·테스트) 동일.

export const BlockType = { P: 'P', H1: 'H1', H2: 'H2', H3: 'H3', QUOTE: 'QUOTE', HR: 'HR' };

// [중립, 정본코드, HTML태그]
const MAP = [
  ['p', BlockType.P, 'p'],
  ['h1', BlockType.H1, 'h1'],
  ['h2', BlockType.H2, 'h2'],
  ['h3', BlockType.H3, 'h3'],
  ['quote', BlockType.QUOTE, 'blockquote'],
  ['hr', BlockType.HR, 'hr'],
];

export const NEUTRAL_TO_CODE = Object.fromEntries(MAP.map(([n, c]) => [n, c]));
export const CODE_TO_NEUTRAL = Object.fromEntries(MAP.map(([n, c]) => [c, n]));
export const NEUTRAL_TO_TAG = Object.fromEntries(MAP.map(([n, , t]) => [n, t]));

// 인라인 마크 — 적용 순서 고정(바깥→안: strong, em)으로 직렬화 결정성 보장.
export const MARKS = ['strong', 'em'];
