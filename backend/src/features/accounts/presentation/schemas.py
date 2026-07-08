"""accounts API 스키마 (camelCase)."""
from uuid import UUID

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class AccountResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)
    id: UUID
    email: str | None
    display_name: str | None
    role: str
    bio: str | None = None
    verified_tier: str = "ALL"
