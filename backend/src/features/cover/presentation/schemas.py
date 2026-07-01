"""cover API 스키마 (camelCase)."""
from src.presentation.schema import CamelSchema


class GenerateCoverRequest(CamelSchema):
    prompt: str


class CoverResponse(CamelSchema):
    cover_url: str
