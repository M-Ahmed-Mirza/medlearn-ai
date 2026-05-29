"""
MedLearn AI - Data Models

Pydantic schemas that mirror data/*.json files and enforce synthetic-data rules.

Public API:
    from agents.models import Learner, Certification, WorkSignal, TeamReport
    from agents.models import RoleCode, DifficultyLevel, BurnoutRisk
"""

from agents.models.certification import Certification, CertificationCatalog
from agents.models.enums import (
    AssessmentOutcome,
    BurnoutRisk,
    CertificationCategory,
    DifficultyLevel,
    ReadinessLevel,
    RoleCode,
)
from agents.models.learner import Learner, LearnerCatalog
from agents.models.team_report import (
    BurnoutRiskSummary,
    DepartmentRollup,
    TeamReport,
    TeamReportCatalog,
)
from agents.models.work_signal import WorkSignal, WorkSignalCatalog

__all__ = [
    # Core models
    "Learner",
    "LearnerCatalog",
    "Certification",
    "CertificationCatalog",
    "WorkSignal",
    "WorkSignalCatalog",
    "TeamReport",
    "TeamReportCatalog",
    "DepartmentRollup",
    "BurnoutRiskSummary",
    # Enums
    "RoleCode",
    "DifficultyLevel",
    "CertificationCategory",
    "AssessmentOutcome",
    "BurnoutRisk",
    "ReadinessLevel",
]
