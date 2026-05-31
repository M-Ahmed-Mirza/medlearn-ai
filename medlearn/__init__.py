"""
MedLearn AI - Agents Package

Top-level public API for MedLearn AI's multi-agent system.

Quick start:
    from medlearn import LearningPathCurator
    curator = LearningPathCurator()
    rec = curator.recommend("CLN-N-001")
    print(rec.target_certification_id)
"""

from medlearn.data_loader import (
    load_all,
    load_certifications,
    load_learners,
    load_team_reports,
    load_work_signals,
)
from medlearn.assessment_agent import AssessmentAgent
from medlearn.engagement_agent import EngagementAgent
from medlearn.grounding import GroundingContext, load_grounding_context
from medlearn.learning_path_curator import LearningPathCurator
from medlearn.manager_insights_agent import ManagerInsightsAgent
from medlearn.study_plan_generator import StudyPlanGenerator

__all__ = [
    # Data loading
    "load_all",
    "load_learners",
    "load_certifications",
    "load_work_signals",
    "load_team_reports",
    # Grounding
    "GroundingContext",
    "load_grounding_context",
    # Agents
    "LearningPathCurator",
    "StudyPlanGenerator",
    "EngagementAgent",
    "AssessmentAgent",
    "ManagerInsightsAgent",
]