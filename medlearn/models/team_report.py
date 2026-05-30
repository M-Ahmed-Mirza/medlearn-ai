"""
MedLearn AI - Team Report Schema

Pydantic models for team-level and department-level aggregate data.
Maps to data/team_reports.json.

These aggregates are critical for the Manager Insights Agent — they let it
reason about team-wide patterns without exposing individual PII.

Used by:
- Manager Insights Agent (primary consumer)
- Engagement Agent (to check team-wide burnout patterns)
"""

from typing import List

from pydantic import BaseModel, Field, field_validator


class BurnoutRiskSummary(BaseModel):
    """Headcount breakdown of burnout categories within a team."""

    high: int = Field(..., ge=0, description="Number of team members at high burnout risk.")
    moderate: int = Field(..., ge=0, description="Number at moderate burnout risk.")
    low: int = Field(..., ge=0, description="Number at low burnout risk.")


class TeamReport(BaseModel):
    """Aggregate metrics for a single clinical team.

    Designed for the Manager Insights Agent to surface team-level patterns
    without exposing individual learners.
    """

    team_id: str = Field(..., description="Synthetic team identifier.", examples=["TEAM-ICU-NIGHT"])
    team_name: str = Field(..., description="Synthetic team display name.")
    department_id: str = Field(..., description="Parent department identifier.")
    team_size: int = Field(..., ge=1, le=100, description="Number of team members.")
    total_pending_certifications: int = Field(
        ..., ge=0, description="Total certifications currently being pursued across the team."
    )
    certifications_due_within_30_days: int = Field(
        ..., ge=0, description="Certs with renewal deadline within 30 days."
    )
    certifications_due_within_90_days: int = Field(
        ..., ge=0, description="Certs with renewal deadline within 90 days."
    )
    team_average_practice_score: int = Field(
        ..., ge=0, le=100, description="Team-wide average of practice assessment scores."
    )
    team_average_study_hours_quarter: int = Field(
        ..., ge=0, description="Team-wide average study hours in the last quarter."
    )
    team_pass_rate: int = Field(
        ..., ge=0, le=100, description="Percentage of recent attempts that passed."
    )
    regulatory_compliance_rate: int = Field(
        ...,
        ge=0,
        le=100,
        description="Percentage of regulatory-required certs currently in-date.",
    )
    average_workload_score: int = Field(..., ge=0, le=100, description="Team-wide workload average.")
    burnout_risk_summary: BurnoutRiskSummary = Field(..., description="Burnout category headcounts.")
    key_insight: str = Field(
        ..., description="Pre-computed natural-language insight for this team."
    )
    synthetic_data: bool = Field(default=True, description="Synthetic-data guardrail flag.")

    @field_validator("team_id")
    @classmethod
    def validate_team_id(cls, v: str) -> str:
        if not v.startswith("TEAM-"):
            raise ValueError(
                "team_id must follow the TEAM-{DEPT}-{SHIFT} synthetic pattern."
            )
        return v

    @field_validator("synthetic_data")
    @classmethod
    def synthetic_flag_must_be_true(cls, v: bool) -> bool:
        if v is not True:
            raise ValueError("synthetic_data must be True.")
        return v


class DepartmentRollup(BaseModel):
    """High-level department metrics rolled up from multiple teams."""

    department_id: str = Field(..., examples=["DEPT-ICU-A"])
    department_name: str
    total_staff: int = Field(..., ge=1)
    overall_compliance_rate: int = Field(..., ge=0, le=100)
    overall_certification_completion_rate: int = Field(..., ge=0, le=100)
    synthetic_data: bool = Field(default=True)

    @field_validator("synthetic_data")
    @classmethod
    def synthetic_flag_must_be_true(cls, v: bool) -> bool:
        if v is not True:
            raise ValueError("synthetic_data must be True.")
        return v


class TeamReportCatalog(BaseModel):
    """Top-level structure of data/team_reports.json."""

    team_reports: List[TeamReport]
    department_rollup: List[DepartmentRollup]
