"""
MedLearn AI - Data Models

Pydantic schemas that mirror data/*.json files and enforce synthetic-data rules.

Public API:
    from medlearn.models import Learner, Certification, WorkSignal, TeamReport
    from medlearn.models import RoleCode, DifficultyLevel, BurnoutRisk
"""

from medlearn.models.agent_response import (
    AlternativeConsidered,
    AssessmentResult,
    Citation,
    CuratorRecommendation,
    EngagementDecision,
    PracticeQuestion,
    StudyPlan,
    StudyWeek,
)
from medlearn.models.certification import Certification, CertificationCatalog
from medlearn.models.enums import (
    AssessmentOutcome,
    BurnoutRisk,
    CertificationCategory,
    DifficultyLevel,
    ReadinessLevel,
    RoleCode,
)
from medlearn.models.learner import Learner, LearnerCatalog
from medlearn.models.team_report import (
    BurnoutRiskSummary,
    DepartmentRollup,
    TeamReport,
    TeamReportCatalog,
)
from medlearn.models.work_signal import WorkSignal, WorkSignalCatalog

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
    # Agent I/O schemas
    "CuratorRecommendation",
    "Citation",
    "AlternativeConsidered",
    "StudyPlan",
    "StudyWeek",
    "EngagementDecision",
    "AssessmentResult",
    "PracticeQuestion",
    # Enums
    "RoleCode",
    "DifficultyLevel",
    "CertificationCategory",
    "AssessmentOutcome",
    "BurnoutRisk",
    "ReadinessLevel",
]