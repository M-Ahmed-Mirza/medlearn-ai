"""
MedLearn AI - Work Signal Schema

Pydantic model for clinical shift patterns and work context.
Maps to data/work_signals.json.

This is the heart of the Work IQ layer — capturing how clinical work rhythms
differ from typical office work (shifts, on-call, focus windows).

Used by:
- Engagement Agent (to time reminders intelligently)
- Study Plan Generator (to find realistic study windows)
- Manager Insights Agent (to spot capacity and burnout risks)
"""

from typing import List

from pydantic import BaseModel, Field, field_validator

from medlearn.models.enums import BurnoutRisk


class WorkSignal(BaseModel):
    """A synthetic work-context record for a single learner.

    Healthcare work rhythms differ fundamentally from office work — these
    signals capture that reality without using any real schedule data.
    """

    learner_id: str = Field(
        ..., description="Reference to the Learner this signal belongs to.", examples=["CLN-N-001"]
    )
    shift_pattern: str = Field(
        ...,
        description="Human-readable description of the shift schedule.",
        examples=["Night Shift (3x12hr/week)"],
    )
    shifts_per_week: int = Field(..., ge=0, le=7, description="Number of clinical shifts per week.")
    shift_hours: int = Field(..., ge=4, le=14, description="Length of each shift in hours.")
    shift_start_time: str = Field(
        ...,
        description="Shift start time in 24hr format, or 'varies' for rotating schedules.",
        examples=["19:00", "varies"],
    )
    shift_end_time: str = Field(
        ..., description="Shift end time in 24hr format, or 'varies'.", examples=["07:00", "varies"]
    )
    meeting_hours_per_week: int = Field(
        ..., ge=0, le=60, description="Weekly meeting hours (rounds, huddles, multidisciplinary)."
    )
    focus_hours_per_week: int = Field(
        ..., ge=0, le=60, description="Weekly hours available for focused study/learning."
    )
    preferred_learning_slot: str = Field(
        ...,
        description="When this learner prefers to study (natural language).",
        examples=["Late Morning (post-shift recovery)"],
    )
    preferred_learning_days: List[str] = Field(
        default_factory=list, description="Days of the week the learner prefers to study."
    )
    on_call_status: bool = Field(
        ..., description="Whether the learner is currently in an on-call rotation."
    )
    current_workload_score: int = Field(
        ...,
        ge=0,
        le=100,
        description="Synthetic workload intensity score (0=light, 100=overloaded).",
    )
    burnout_risk_indicator: BurnoutRisk = Field(
        ..., description="Categorical burnout risk derived from workload + history."
    )
    synthetic_data: bool = Field(default=True, description="Synthetic-data guardrail flag.")

    @field_validator("learner_id")
    @classmethod
    def validate_learner_reference(cls, v: str) -> str:
        if not v.startswith("CLN-"):
            raise ValueError(
                "learner_id must follow the CLN-{X}-{NNN} synthetic pattern."
            )
        return v

    @field_validator("synthetic_data")
    @classmethod
    def synthetic_flag_must_be_true(cls, v: bool) -> bool:
        if v is not True:
            raise ValueError("synthetic_data must be True.")
        return v


class WorkSignalCatalog(BaseModel):
    """Top-level structure of data/work_signals.json."""

    work_signals: List[WorkSignal]
