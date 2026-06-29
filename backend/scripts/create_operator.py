"""운영자(potato) 계정 생성 — 공개 가입 없음(닫힌 영역). 서버에서 1회 실행.

사용:
  .venv312/bin/python scripts/create_operator.py <email> <name> [--role OPERATOR|DEVELOPER]
비밀번호는 프롬프트로 입력(에코 없음). 첫 계정은 보통 --role DEVELOPER.
"""
import argparse
import asyncio
import getpass
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config.database import get_session_factory  # noqa: E402
from src.features.potato.application.password import hash_password  # noqa: E402
from src.features.potato.domain.models import ROLES  # noqa: E402
from src.features.potato.infrastructure.operator_repo import SqlOperatorRepository  # noqa: E402


async def main() -> None:
    ap = argparse.ArgumentParser(description="운영자 계정 생성")
    ap.add_argument("email")
    ap.add_argument("name")
    ap.add_argument("--role", default="OPERATOR")
    args = ap.parse_args()

    role = args.role.upper()
    if role not in ROLES:
        print(f"role 은 {sorted(ROLES)} 중 하나여야 합니다.")
        sys.exit(1)

    password = getpass.getpass("password: ")
    if len(password) < 8:
        print("비밀번호는 8자 이상이어야 합니다.")
        sys.exit(1)
    if getpass.getpass("password (확인): ") != password:
        print("비밀번호가 일치하지 않습니다.")
        sys.exit(1)

    factory = get_session_factory()
    async with factory() as session:
        repo = SqlOperatorRepository(session)
        if await repo.get_by_email(args.email):
            print(f"이미 존재하는 운영자입니다: {args.email}")
            sys.exit(1)
        operator = await repo.create(
            email=args.email,
            name=args.name,
            role_cd=role,
            password_hash=hash_password(password),
        )
    print(f"✅ 운영자 생성 — {operator.email} ({operator.role_cd}) id={operator.id}")


if __name__ == "__main__":
    asyncio.run(main())
