"""
MedLearn AI - Shared Enumerations

Centralized enums used across all Pydantic models.
Keeping these in one place ensures consistency and makes future changes easy.
"""

from enum import Enum


class RoleCode(str, Enum):
    """Clinical role categories supported by MedLearn AI."""

    CRITICAL_CARE_RN = "RN_CCU"
    HOSPITAL_PHARMACIST = "PHARM_HOSP"
    MEDICAL_LAB_TECH = "MLT_LAB"


class DifficultyLevel(str, Enum):
    """Certification difficulty tiers used by Study Plan Generator."""

    BEGINNER = "Beginner"
    INTERMEDIATE = "Intermediate"
    ADVANCED = "Advanced"


class CertificationCategory(str, Enum):
    """High-level grouping of certification types."""

    CLINICAL_SPECIALTY = "Clinical Specialty"
    EMERGENCY_RESPONSE = "Emergency Response"
    COMPLIANCE = "Compliance"


class AssessmentOutcome(str, Enum):
    """Result of an assessment attempt."""

    PASS = "Pass"
    FAIL = "Fail"
    NOT_ATTEMPTED = "Not Attempted"


class BurnoutRisk(str, Enum):
    """Burnout risk classification used by Engagement Agent."""

    LOW = "Low"
    MODERATE = "Moderate"
    HIGH = "High"


class ReadinessLevel(str, Enum):
    """Assessment Agent's readiness recommendation."""

    NOT_READY = "Not Ready"
    APPROACHING_READY = "Approaching Ready"
    READY = "Ready"
    EXAM_RECOMMENDED = "Exam Recommended"
