from __future__ import annotations

from pydantic import BaseModel, field_validator

from app.pipeline.sanitizer import (
    sanitize_company_name,
    sanitize_description,
    sanitize_text,
    sanitize_url,
)


class CreateAnalysisRequest(BaseModel):
    company_name: str
    website_url: str
    description: str
    target_market: str | None = None
    known_competitors: list[str] = []
    analysis_depth: str = "standard"

    @field_validator("company_name")
    @classmethod
    def validate_company_name(cls, v: str) -> str:
        v = sanitize_company_name(v)
        if not v:
            raise ValueError("company_name cannot be empty")
        return v

    @field_validator("website_url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        return sanitize_url(v)

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str) -> str:
        if len(v) > 500:
            raise ValueError("description must be 500 characters or less")
        return sanitize_description(v)

    @field_validator("target_market")
    @classmethod
    def validate_target_market(cls, v: str | None) -> str | None:
        if v is not None:
            return sanitize_text(v, max_length=100)
        return v

    @field_validator("known_competitors")
    @classmethod
    def validate_competitors(cls, v: list[str]) -> list[str]:
        if len(v) > 5:
            raise ValueError("known_competitors must have 5 or fewer entries")
        return [sanitize_text(c, max_length=100) for c in v]

    @field_validator("analysis_depth")
    @classmethod
    def validate_depth(cls, v: str) -> str:
        if v not in ("quick", "standard", "deep"):
            raise ValueError("analysis_depth must be quick, standard, or deep")
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
