"""
MedLearn AI - Agents Package

Top-level public API for MedLearn AI's multi-agent system.
The 5 agents (to be added in Phase 2) will live alongside this file.

Quick start:
    from agents import load_all
    data = load_all()
    print(f"Loaded {len(data['learners'].learners)} learners.")
"""

from agents.data_loader import (
    load_all,
    load_certifications,
    load_learners,
    load_team_reports,
    load_work_signals,
)

__all__ = [
    "load_all",
    "load_learners",
    "load_certifications",
    "load_work_signals",
    "load_team_reports",
]
