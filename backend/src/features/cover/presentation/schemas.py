"""cover API 스키마 (camelCase)."""
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class _Camel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class GenerateCoverRequest(_Camel):
    prompt: str


class CoverResponse(_Camel):
    cover_url: str
