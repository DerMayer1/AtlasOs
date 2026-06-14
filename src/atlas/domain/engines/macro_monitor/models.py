"""Typed inputs for the Macro Monitor engine."""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class MacroMonitorParams(BaseModel):
    """Configuration for deterministic macro-state monitoring."""

    short_window_months: int = Field(default=3, ge=1, le=12)
    long_window_months: int = Field(default=12, ge=6, le=36)
    alert_z_threshold: float = Field(default=1.5, ge=0.5, le=4.0)
    change_z_threshold: float = Field(default=1.0, ge=0.25, le=4.0)
    comparison_snapshot_id: str | None = None

    @model_validator(mode="after")
    def validate_windows(self) -> MacroMonitorParams:
        if self.long_window_months < self.short_window_months:
            raise ValueError(
                "long_window_months must be greater than or equal to "
                "short_window_months"
            )
        return self
