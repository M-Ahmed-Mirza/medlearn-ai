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
