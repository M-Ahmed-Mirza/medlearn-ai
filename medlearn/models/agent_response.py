"""
MedLearn AI - Agent Response Schemas

Structured outputs every agent must return. Includes confidence scoring,
cited sources, and alternatives considered — the V1.5 differentiators
that make our reasoning visible to judges.
"""

from typing import List, Optional

from pydantic import BaseModel, Field

from medlearn.models.enums import ReadinessLevel


class Citation(BaseModel):
    """A single citation backing an agent's reasoning."""

    source_document: str = Field(
        ..., description="Path or identifier of the source doc, e.g. 'clinical_certification_guide.md'."
    )
    section: Optional[str] = Field(
        default=None,
        description="Section reference within the doc, e.g. 'Section 2.1 — Critical Care RN'.",
    )
    excerpt: Optional[str] = Field(
        default=None, description="Short verbatim excerpt supporting the claim."
    )


class AlternativeConsidered(BaseModel):
    """An option the agent evaluated but did not pick. Boosts reasoning transparency."""

    option: str = Field(..., description="Brief description of the alternative.")
    rejected_because: str = Field(..., description="Why this option was not chosen.")


class CuratorRecommendation(BaseModel):
    """Structured output from the Learning Path Curator Agent.

    This schema is what GPT-4o will be forced to return — guaranteeing
    we always get cited, confidence-scored, alternative-aware recommendations.
    """

    learner_id: str = Field(..., description="The learner this recommendation is for.")
    target_certification_id: str = Field(
        ..., description="The cert ID the learner should pursue, e.g. 'CCRN-2024'."
    )
    target_certification_name: str = Field(
        ..., description="Human-readable cert name."
    )
    rationale: str = Field(
        ...,
        description="2-4 sentence plain-English explanation of WHY this cert is recommended.",
    )
    skills_to_acquire: List[str] = Field(
        ..., min_length=1, description="Skills the learner will gain by completing this cert."
    )
    recommended_study_hours: int = Field(
        ..., ge=1, description="Total study hours recommended for this cert."
    )
    prerequisites_status: str = Field(
        ...,
        description="One of: 'All prerequisites met', 'Some missing', 'Prerequisites unclear'.",
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Agent's confidence in this recommendation (0.0 to 1.0).",
    )
    citations: List[Citation] = Field(
        default_factory=list,
        description="Source documents and sections cited in the rationale.",
    )
    alternatives_considered: List[AlternativeConsidered] = Field(
        default_factory=list,
        description="Other options the agent thought about but rejected.",
    )
    safety_flags: List[str] = Field(
        default_factory=list,
        description="Any safety/risk concerns flagged for human review.",
    )


# ============================================================================
# Study Plan Generator schemas
# ============================================================================


class StudyWeek(BaseModel):
    """A single week in a study plan."""

    week_number: int = Field(..., ge=1, description="Sequential week index, starting at 1.")
    hours_allocated: float = Field(
        ..., ge=0.0, le=40.0, description="Total study hours scheduled this week."
    )
    focus_topics: List[str] = Field(
        ..., min_length=1, description="Specific skills/topics to study this week."
    )
    sessions_per_week: int = Field(
        ..., ge=1, le=14, description="Number of distinct study sessions across the week."
    )
    milestone: Optional[str] = Field(
        default=None,
        description="Concrete checkpoint for this week (e.g. 'Complete Hemodynamics module', 'First practice test').",
    )


class StudyPlan(BaseModel):
    """Structured output from the Study Plan Generator Agent.

    A realistic, shift-aware study plan that respects the learner's clinical
    workload, burnout indicators, and preferred learning windows.
    """

    learner_id: str = Field(..., description="The learner this plan is for.")
    target_certification_id: str = Field(
        ..., description="The cert this plan prepares the learner for, e.g. 'CCRN-2024'."
    )
    target_certification_name: str = Field(..., description="Human-readable cert name.")
    total_weeks: int = Field(
        ..., ge=1, le=52, description="Total number of weeks in the plan."
    )
    total_study_hours: float = Field(
        ..., ge=1.0, description="Total study hours allocated across the entire plan."
    )
    weekly_hour_target: float = Field(
        ...,
        ge=0.5,
        le=40.0,
        description="Average target hours per week (informational summary).",
    )
    preferred_study_window: str = Field(
        ...,
        description="When in the week/day this learner is scheduled to study, in plain English.",
    )
    weeks: List[StudyWeek] = Field(
        ...,
        min_length=1,
        description="Detailed week-by-week schedule. Length must equal total_weeks.",
    )
    schedule_feasibility: str = Field(
        ...,
        description="One of: 'Comfortably achievable', 'Tight but feasible', 'High risk — exceeds available focus hours'.",
    )
    rationale: str = Field(
        ...,
        description="2-4 sentence plain-English explanation of HOW the plan was built and key trade-offs.",
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Agent's confidence in the plan's feasibility (0.0 to 1.0).",
    )
    citations: List[Citation] = Field(
        default_factory=list,
        description="Source documents referenced when designing the plan.",
    )
    safety_flags: List[str] = Field(
        default_factory=list,
        description="Workload/burnout/timeline risks flagged for human review.",
    )