// ProseMirror 문서 ↔ 중립 doc 변환. prosemirror-model 만 의존 → DOM 없이 노드에서 테스트 가능.
// 중립 doc 은 core/serialize 의 정본 직렬화로 이어진다: PM ↔ 중립 ↔ 정본{type,html}.
import { MARKS } from '../core/blocks';
import { schema } from './schema';

const NODE_TO_NEUTRAL = { paragraph: 'p', blockquote: 'quote' };

function inlineToSpans(node) {
  const spans = [];
  node.forEach((child) => {
    if (!child.isText) return;
    spans.push({ text: child.text, marks: MARKS.filter((m) => child.marks.some((mk) => mk.type.name === m)) });
  });
  return spans;
}

// PM doc(Node) → 중립 doc
export function pmToNeutral(pmDoc) {
  const blocks = [];
  pmDoc.forEach((node) => {
    if (node.type.name === 'horizontal_rule') {
      blocks.push({ type: 'hr' });
      return;
    }
    const type = node.type.name === 'heading' ? `h${node.attrs.level}` : NODE_TO_NEUTRAL[node.type.name];
    blocks.push({ type, spans: inlineToSpans(node) });
  });
  return { blocks };
}

// 중립 doc → PM doc(Node) (기존 책 불러오기·초기 시드)
export function neutralToPmDoc(doc) {
  const content = (doc.blocks || []).map((b) => {
    if (b.type === 'hr') return schema.nodes.horizontal_rule.create();
    const inline = (b.spans || [])
      .filter((s) => s.text.length) // PM 은 빈 텍스트 노드 불허
      .map((s) => schema.text(s.text, s.marks.map((m) => schema.marks[m].create())));
    if (b.type[0] === 'h') return schema.nodes.heading.create({ level: Number(b.type[1]) }, inline);
    if (b.type === 'quote') return schema.nodes.blockquote.create(null, inline);
    return schema.nodes.paragraph.create(null, inline);
  });
  return schema.nodes.doc.create(null, content);
}
