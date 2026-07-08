// 페이지별 동적 메타 (React 19 네이티브 — react-helmet 불필요).
// React 19는 컴포넌트 트리 어디서든 <title>/<meta>/<link> 를 렌더하면 자동으로 <head>로
// hoist 한다(공식 지원, https://react.dev/reference/react-dom/components/title).
//
// ⚠️ 순수 SPA라 이 클라이언트 메타는 Googlebot(JS를 실행하는 크롤러)엔 반영되지만,
// 카카오톡·페이스북 등 JS를 실행하지 않는 링크 미리보기 크롤러에는 반영되지 않는다.
// (이들은 최초 HTML 응답만 파싱한다.) 소셜 미리보기 정확도를 높이려면 프리렌더
// (Cloudflare Function 등으로 요청 시점에 og 메타를 주입)가 별도로 필요 — 후속 과제.
// index.html의 정적 og/twitter 메타는 이 프리렌더 전까지의 폴백으로 그대로 유지한다.
export function PageMeta({ title, description, image, url }) {
  return (
    <>
      {title && <title>{title}</title>}
      {description && <meta name="description" content={description} />}
      {title && <meta property="og:title" content={title} />}
      {description && <meta property="og:description" content={description} />}
      {image && <meta property="og:image" content={image} />}
      {url && <meta property="og:url" content={url} />}
      <meta name="twitter:card" content="summary_large_image" />
      {title && <meta name="twitter:title" content={title} />}
      {description && <meta name="twitter:description" content={description} />}
      {image && <meta name="twitter:image" content={image} />}
    </>
  );
}
