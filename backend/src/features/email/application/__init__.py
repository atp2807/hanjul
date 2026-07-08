"""email 피처는 application 서비스가 없다(로직이 domain 순수함수 + infrastructure 얇은 훅뿐).

빈 패키지만 존재 — import-linter의 layers 계약(pyproject.toml)이 각 feature 컨테이너에
presentation/infrastructure/application/domain 4계층 모듈이 모두 있을 것을 요구한다.
"""
