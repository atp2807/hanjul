// dialect 정규화 테스트 — 허용 태그만 남고 나머지는 unwrap/제거.
import { describe, it, expect } from 'vitest';
import { normalizeHtml, sanitizeUrl } from './dialect.js';

describe('normalizeHtml', () => {
  it('script 는 내용째 제거', () => {
    const out = normalizeHtml('<p>안녕<script>alert(1)</script></p>');
    expect(out).not.toContain('script');
    expect(out).toContain('안녕');
  });

  it('알 수 없는 태그(div/span)는 unwrap — 텍스트 보존', () => {
    const out = normalizeHtml('<div><span>hello</span> world</div>');
    expect(out).not.toContain('<div');
    expect(out).not.toContain('<span');
    expect(out).toContain('hello');
    expect(out).toContain('world');
  });

  it('허용 인라인(strong/em/a)은 유지', () => {
    const out = normalizeHtml('<p><strong>굵게</strong> <em>기울임</em></p>');
    expect(out).toContain('<strong>굵게</strong>');
    expect(out).toContain('<em>기울임</em>');
  });

  it('b/i 는 strong/em 으로 정규화 (execCommand bold/italic 산출물)', () => {
    // execCommand('bold'/'italic') 이 <b>/<i> 를 만드는 브라우저 대응 —
    // 붙여넣기/드롭 정규화에서 정본 인라인으로 변환돼야 왕복 손실이 없다.
    const out = normalizeHtml('<p>앞 <b>굵게</b> 뒤 <i>기울임</i></p>');
    expect(out).toContain('<strong>굵게</strong>');
    expect(out).toContain('<em>기울임</em>');
    expect(out).not.toContain('<b>');
    expect(out).not.toContain('<i>');
  });

  it('중첩 b>i 도 strong>em 으로 정규화', () => {
    const out = normalizeHtml('<p><b><i>둘다</i></b></p>');
    expect(out).toContain('<strong><em>둘다</em></strong>');
  });

  it('허용 블록(h1/blockquote/ul)은 유지', () => {
    const out = normalizeHtml('<h1>제목</h1><blockquote>인용</blockquote><ul><li>항목</li></ul>');
    expect(out).toContain('<h1>제목</h1>');
    expect(out).toContain('<blockquote>인용</blockquote>');
    expect(out).toContain('<li>항목</li>');
  });

  it('이벤트 핸들러/미허용 속성 제거', () => {
    const out = normalizeHtml('<p onclick="evil()" class="x">텍스트</p>');
    expect(out).not.toContain('onclick');
    expect(out).not.toContain('class');
    expect(out).toContain('텍스트');
  });

  it('javascript: 링크는 href 제거 (a 는 남되 무해)', () => {
    const out = normalizeHtml('<a href="javascript:alert(1)">클릭</a>');
    expect(out).not.toContain('javascript');
    expect(out).toContain('클릭');
  });

  it('http(s)/상대 링크는 href 유지', () => {
    const out = normalizeHtml('<a href="https://example.com">링크</a>');
    expect(out).toContain('href="https://example.com"');
  });

  it('표 셀의 colspan/rowspan 유지', () => {
    const out = normalizeHtml('<table><tr><td colspan="2">넓게</td></tr></table>');
    expect(out).toContain('colspan="2"');
    expect(out).toContain('넓게');
  });

  it('code 의 language-* class 만 유지', () => {
    const out = normalizeHtml('<pre><code class="language-python foo">x=1</code></pre>');
    expect(out).toContain('language-python');
    expect(out).not.toContain('foo');
  });

  it('표 왕복 — thead/tbody/tr/th/td 구조 보존', () => {
    const table =
      '<table><thead><tr><th>H1</th><th>H2</th></tr></thead>' +
      '<tbody><tr><td>a</td><td>b</td></tr><tr><td>c</td><td>d</td></tr></tbody></table>';
    const out = normalizeHtml(table);
    expect(out).toContain('<thead>');
    expect(out).toContain('<tbody>');
    expect(out).toContain('<th>H1</th>');
    expect(out).toContain('<td>d</td>');
    // 왕복 안정: 정규화된 산출을 다시 넣어도 동일 구조.
    expect(normalizeHtml(out)).toBe(out);
  });

  it('삽입한 img(/media/) src·alt 보존', () => {
    const out = normalizeHtml('<img src="/media/abc123" alt="사진">');
    expect(out).toContain('src="/media/abc123"');
    expect(out).toContain('alt="사진"');
  });

  it('img 의 javascript: src 는 제거(상대/http(s) 만 통과)', () => {
    const out = normalizeHtml('<img src="javascript:alert(1)" alt="x">');
    expect(out).not.toContain('javascript');
  });
});

describe('sanitizeUrl', () => {
  it('상대경로 통과', () => expect(sanitizeUrl('/a/b')).toBe('/a/b'));
  it('http 통과', () => expect(sanitizeUrl('http://x')).toBe('http://x'));
  it('javascript 차단', () => expect(sanitizeUrl('javascript:alert(1)')).toBe(''));
  it('data 차단', () => expect(sanitizeUrl('data:text/html,x')).toBe(''));
});
