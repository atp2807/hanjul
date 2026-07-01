// 사업자정보 — 전자상거래법 §10 사이버몰 운영자 표시 + 법률문서·푸터 단일 소스.
// ⚠️ '________' 항목은 실제 값으로 채워넣기. (사업자등록증·통신판매신고·출판사신고 참조)
export const BUSINESS = {
  service: '한줄', // 서비스(사이버몰) 이름
  company: '포테이토크래프트', // 상호(사업자등록증 기준)
  ceo: '박연미', // 대표자 성명
  bizNo: '370-08-03144', // 사업자등록번호
  mailOrderNo: '신고 예정', // 통신판매업 신고번호 (통신판매 신고 후 기입)
  publisherNo: '신고 예정', // 출판사 신고번호 / 발행자번호 (출판사 신고 후)
  address: '경기도 화성시 효행로 1068, 6층 604-G115호(병점동, 리더스프라자)', // 사업장 소재지
  tel: '________', // 대표 전화 (미확정)
  email: 'help@hanjul.io', // 고객 이메일 (도메인 보유 — 실제 사용 주소 확인)
  host: 'Amazon Web Services · Cloudflare', // 호스팅서비스 제공자
  // 개인정보 보호책임자(CPO) — 개인정보보호법 §30①8
  privacyOfficer: { name: '________', title: '대표', email: 'privacy@hanjul.io' },
  // 저작권 침해 신고 수신인 — 저작권법 §103④
  copyrightAgent: { name: '________', email: 'report@hanjul.io' },
};
