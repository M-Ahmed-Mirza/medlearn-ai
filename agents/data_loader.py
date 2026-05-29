"""
MedLearn AI - Data Loader

Single source of truth for loading synthetic data files into validated
Pydantic models. Every agent should use these helpers instead of reading
JSON directly — that way validation happens once and consistently.

Usage:
    from agents.data_loader import load_learners, load_certifications

    learners = load_learners()           # Returns LearnerCatalog
    certs = load_certifications()        # Returns CertificationCatalog
"""

import json
from pathlib import Path
from typing import Any, Dict

from agents.models import (
    CertificationCatalog,
    LearnerCatalog,
    TeamReportCatalog,
    WorkSignalCatalog,
)

# Project root is two levels above this file: agents/data_loader.py -> medlearn-ai/
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"


def _load_json(filename: str) -> Dict[str, Any]:
    """Load a JSON file from the data directory. Strips the optional _metadata key."""
    file_path = DATA_DIR / filename
    if not file_path.exists():
        raise FileNotFoundError(
            f"Synthetic data file not found: {file_path}. "
            f"Expected location: {DATA_DIR}"
        )
    with file_path.open(encoding="utf-8") as f:
        data = json.load(f)
    # Strip the descriptive metadata block — it's documentation, not schema data
    data.pop("_metadata", None)
    return data


def load_learners() -> LearnerCatalog:
    """Load and validate data/learners.json."""
    return LearnerCatalog(**_load_json("learners.json"))


def load_certifications() -> CertificationCatalog:
    """Load and validate data/certifications.json."""
    return CertificationCatalog(**_load_json("certifications.json"))


def load_work_signals() -> WorkSignalCatalog:
    """Load and validate data/work_signals.json."""
    return WorkSignalCatalog(**_load_json("work_signals.json"))


def load_team_reports() -> TeamReportCatalog:
    """Load and validate data/team_reports.json."""
    return TeamReportCatalog(**_load_json("team_reports.json"))


def load_all() -> Dict[str, Any]:
    """Convenience: load every dataset at once.

    Returns a dict so agents can pick the data they need:
        data = load_all()
        for learner in data["learners"].learners:
            ...
    """
    return {
        "learners": load_learners(),
        "certifications": load_certifications(),
        "work_signals": load_work_signals(),
        "team_reports": load_team_reports(),
    }
