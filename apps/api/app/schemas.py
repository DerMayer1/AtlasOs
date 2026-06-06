from __future__ import annotations

from pydantic import BaseModel, HttpUrl, field_validator


class CreateAnalysisRequest(BaseModel):
    company_name: str
    website_url: str
    description: str
    target_market: str | None = None
    known_competitors: list[str] = []
    analysis_depth: str = "standard"

    @field_validator("company_name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("company_name cannot be empty")
        return v.strip()

    @field_validator("description")
    @classmethod
    def description_length(cls, v: str) -> str:
        if len(v) > 500:
            raise ValueError("description must be 500 characters or less")
        return v

    @field_validator("analysis_depth")
    @classmethod
    def valid_depth(cls, v: str) -> str:
        if v not in ("quick", "standard", "deep"):
            raise ValueError("analysis_depth must be quick, standard, or deep")
        return v

    @field_validator("known_competitors")
    @classmethod
    def max_competitors(cls, v: list[str]) -> list[str]:
        if len(v) > 5:
            raise ValueError("known_competitors must have 5 or fewer entries")
        return v


class ExportMemoRequest(BaseModel):
    format: str

    @field_validator("format")
    @classmethod
    def valid_format(cls, v: str) -> str:
        if v not in ("pdf", "markdown"):
            raise ValueError("format must be pdf or markdown")
        return v


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict = {}


class ErrorResponse(BaseModel):
    error: ErrorDetail
