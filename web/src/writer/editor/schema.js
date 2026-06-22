// ProseMirror 스키마 — 정본 블록 집합에 정확히 맞춤 (p/h1~3/blockquote/hr + strong/em).
// schema-basic 대신 우리 블록만 정의 = 책임 명확 + 정본 매핑 1:1.
import { Schema } from 'prosemirror-model';

export const schema = new Schema({
  nodes: {
    doc: { content: 'block+' },
    paragraph: { group: 'block', content: 'inline*', parseDOM: [{ tag: 'p' }], toDOM: () => ['p', 0] },
    heading: {
      group: 'block',
      content: 'inline*',
      attrs: { level: { default: 1 } },
      defining: true,
      parseDOM: [1, 2, 3].map((l) => ({ tag: `h${l}`, attrs: { level: l } })),
      toDOM: (n) => [`h${n.attrs.level}`, 0],
    },
    blockquote: { group: 'block', content: 'inline*', parseDOM: [{ tag: 'blockquote' }], toDOM: () => ['blockquote', 0] },
    horizontal_rule: { group: 'block', parseDOM: [{ tag: 'hr' }], toDOM: () => ['hr'] },
    text: { group: 'inline' },
  },
  marks: {
    strong: { parseDOM: [{ tag: 'strong' }, { tag: 'b' }], toDOM: () => ['strong', 0] },
    em: { parseDOM: [{ tag: 'em' }, { tag: 'i' }], toDOM: () => ['em', 0] },
  },
});
