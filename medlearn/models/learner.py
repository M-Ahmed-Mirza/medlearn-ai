"""
MedLearn AI - Learner Schema

Pydantic model for clinical staff (synthetic) profiles.
Maps to data/learners.json.

Used by:
- Learning Path Curator (to understand who is learning)
- Study Plan Generator (to build personalized schedules)
- Assessment Agent (to track readiness)
- Manager Insights Agent (for aggregate views)
"""

from typing import List

from pydantic import BaseModel, Field, field_validator

from medlearn.models.enums import AssessmentOutcome, RoleCode


class Learner(BaseModel):
    """A synthetic clinical staff member.

    All identifiers must follow the CLN-{role_initial}-{number} pattern
    to make the synthetic nature obvious (per hackathon synthetic-data rules).
    """

    learner_id: str = Field(
        ...,
        description="Synthetic identifier, e.g. CLN-N-001 (nurse), CLN-P-001 (pharmacist), CLN-L-001 (lab tech).",
        examples=["CLN-N-001"],
    )
    display_name: str = Field(
        ...,
        description="Synthetic display name (never a real person's name).",
        examples=["Synthetic Learner N-001"],
    )
    role: str = Field(
        ..., description="Human-readable role description.", examples=["Critical Care Registered Nurse"]
    )
    role_code: RoleCode = Field(..., description="Machine-readable role enum.")
    department_id: str = Field(..., description="Synthetic department identifier.", examples=["DEPT-ICU-A"])
    team_id: str = Field(..., description="Synthetic team identifier.", examples=["TEAM-ICU-NIGHT"])
    experience_years: int = Field(..., ge=0, le=50, description="Years of experience in current role.")
    current_certifications: List[str] = Field(
        default_factory=list,
        description="IDs of certifications the learner already holds.",
    )
    pending_certifications: List[str] = Field(
        default_factory=list,
        description="IDs of certifications the learner is pursuing.",
    )
    practice_score_avg: int = Field(
        ..., ge=0, le=100, description="Average practice assessment score (0-100)."
    )
    hours_studied_last_quarter: int = Field(
        ..., ge=0, description="Hours studied in the last 90 days."
    )
    last_assessment_outcome: AssessmentOutcome = Field(
        default=AssessmentOutcome.NOT_ATTEMPTED,
        description="Outcome of the most recent assessment attempt.",
    )
    renewal_due_in_days: int = Field(
        ..., description="Days until the soonest pending certification is due. Negative if overdue.",
    )
    synthetic_data: bool = Field(
        default=True,
        description="Explicit flag confirming this is synthetic data. Must always be True.",
    )

    @field_validator("learner_id")
    @classmethod
    def validate_synthetic_learner_id(cls, v: str) -> str:
        """Enforce the CLN-{X}-{NNN} pattern so synthetic data stays obvious."""
        if not v.startswith("CLN-"):
            raise ValueError(
                "learner_id must start with 'CLN-' to enforce synthetic-data convention. "
                "See data/README.md for the naming pattern."
            )
        return v

    @field_validator("synthetic_data")
    @classmethod
    def synthetic_flag_must_be_true(cls, v: bool) -> bool:
        """Enforce the synthetic flag. This is a hackathon-compliance guardrail."""
        if v is not True:
            raise ValueError(
                "synthetic_data must be True. MedLearn AI does not handle real patient or employee data."
            )
        return v


class LearnerCatalog(BaseModel):
    """Top-level structure of data/learners.json."""

    learners: List[Learner]
