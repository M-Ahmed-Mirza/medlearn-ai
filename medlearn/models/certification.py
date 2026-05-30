"""
MedLearn AI - Certification Schema

Pydantic model for healthcare certification catalog.
Maps to data/certifications.json.

This is the heart of the Fabric IQ semantic layer — relationships between
roles, skills, certifications, prerequisites, and renewal cycles all live here.

Used by:
- Learning Path Curator (to recommend pathways)
- Study Plan Generator (to allocate study hours)
- Assessment Agent (to generate role-appropriate questions)
"""

from typing import List

from pydantic import BaseModel, Field, field_validator

from medlearn.models.enums import CertificationCategory, DifficultyLevel, RoleCode


class Certification(BaseModel):
    """A synthetic healthcare certification record.

    Powers Fabric IQ's semantic relationships between role, skill, hours, and cycle.
    """

    id: str = Field(
        ...,
        description="Synthetic cert identifier, e.g. CCRN-2024, HIPAA-ANNUAL-2026.",
        examples=["CCRN-2024"],
    )
    display_name: str = Field(..., description="Human-readable certification name.")
    category: CertificationCategory = Field(..., description="High-level grouping.")
    applies_to_roles: List[RoleCode] = Field(
        ...,
        min_length=1,
        description="Which clinical roles this certification is relevant for.",
    )
    skills: List[str] = Field(
        ...,
        min_length=1,
        description="Skill domains covered by this certification.",
    )
    recommended_study_hours: int = Field(
        ..., ge=1, le=200, description="Recommended total study hours (synthetic baseline)."
    )
    minimum_passing_score: int = Field(
        ..., ge=50, le=100, description="Minimum practice score considered 'ready' (synthetic)."
    )
    renewal_cycle_years: int = Field(
        ..., ge=1, le=10, description="How often this certification must be renewed."
    )
    prerequisites: List[str] = Field(
        default_factory=list,
        description="IDs of certifications that must be held before pursuing this one.",
    )
    difficulty_level: DifficultyLevel = Field(..., description="Difficulty tier.")
    regulatory_requirement: bool = Field(
        ...,
        description="True if this is a regulatory mandate (missing it has compliance implications).",
    )
    synthetic_data: bool = Field(default=True, description="Synthetic-data guardrail flag.")

    @field_validator("id")
    @classmethod
    def validate_cert_id(cls, v: str) -> str:
        """Cert IDs should be uppercase with hyphens to stay readable."""
        if not v or v != v.upper().replace(" ", ""):
            raise ValueError(
                f"Certification id '{v}' should be uppercase with no spaces. See data/README.md."
            )
        return v

    @field_validator("synthetic_data")
    @classmethod
    def synthetic_flag_must_be_true(cls, v: bool) -> bool:
        if v is not True:
            raise ValueError("synthetic_data must be True.")
        return v


class CertificationCatalog(BaseModel):
    """Top-level structure of data/certifications.json."""

    certifications: List[Certification]
