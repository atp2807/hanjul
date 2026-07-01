"""API 스키마 공통 베이스 — 전 피처가 재사용(중복 제거·일관성).

camelCase 별칭(프론트 JSON) + snake_case 입력 허용(populate_by_name) +
ORM 객체 직접 매핑(from_attributes) 통일.
"""
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelSchema(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )
