"""거래 이메일(주문확인·출금상태) 발송 인프라.

domain(순수 템플릿+포트) / infrastructure(SMTP·데모 어댑터 + 각 피처용 훅 구현) /
presentation(DI 조립) — application 은 빈 패키지(로직이 순수 함수+얇은 훅뿐이라 서비스
불필요, import-linter layers 계약 때문에 모듈 자체는 존재).
"""
