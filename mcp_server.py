"""
MedLearn AI - MCP Server

Exposes MedLearn AI's reasoning agents as Model Context Protocol (MCP) tools,
so any MCP-compliant client (Claude Desktop, Cursor, VS Code, etc.) can invoke
the system's capabilities through the standard protocol.

Built on the official `mcp` SDK's FastMCP framework. Each tool wraps an agent's
public method (or the full orchestrator pipeline), validates inputs against the
known catalog, runs the agent, and returns the structured Pydantic result as
JSON.

Tools exposed:
    recommend_certification(learner_id, target_cert_id?)  -> Curator
    build_study_plan(learner_id, target_cert_id)          -> Study Plan
    decide_engagement(learner_id, occasion)               -> Engagement (ethical)
    assess_readiness(learner_id, target_cert_id)          -> Assessment
    analyze_team(team_id, escalation_note?)               -> Manager Insights
    run_full_journey(learner_id, target_cert_id?)         -> Orchestrator pipeline

Resources exposed (for ID discovery by the client):
    medlearn://learners        -> list of valid learner IDs + roles
    medlearn://certifications  -> list of valid certification IDs

Run (stdio transport, for Claude Desktop):
    python -m scripts.run_mcp_server
Or directly with the MCP CLI / Inspector:
    mcp dev mcp_server.py

SECURITY NOTE:
    Tool inputs arrive from an LLM, not directly from a trusted user, so every
    tool validates learner_id / cert_id / team_id against the loaded catalog
    before invoking an agent. Unknown IDs return a clear error rather than
    reaching the model.
"""

from __future__ import annotations

import json
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

from mcp.server.fastmcp import FastMCP

from medlearn.data_loader import (
    load_certifications,
    load_learners,
    load_team_reports,
)

mcp = FastMCP("MedLearn AI")


# ---------------------------------------------------------------------------
# Lazy agent/orchestrator construction
# ---------------------------------------------------------------------------
# Agents are built on first use (not import) so the server starts instantly
# and only pays the Azure-client cost when a tool is actually called.

_orchestrator = None


def _get_orchestrator():
    global _orchestrator
    if _orchestrator is None:
        from medlearn.orchestrator import Orchestrator

        _orchestrator = Orchestrator(verbose=False)
    return _orchestrator


# ---------------------------------------------------------------------------
# Input validation helpers (untrusted-input discipline)
# ---------------------------------------------------------------------------


def _valid_learner_ids() -> set[str]:
    return {l.learner_id for l in load_learners().learners}


def _valid_cert_ids() -> set[str]:
    return {c.id for c in load_certifications().certifications}


def _valid_team_ids() -> set[str]:
    return {t.team_id for t in load_team_reports().team_reports}


def _err(message: str) -> str:
    return json.dumps({"error": message})


def _ok(model) -> str:
    """Serialize a Pydantic model result to JSON."""
    return model.model_dump_json(indent=2)


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@mcp.tool()
def recommend_certification(
    learner_id: str, target_cert_id: Optional[str] = None
) -> str:
    """Recommend the next certification for a clinical learner.

    Runs the Learning Path Curator agent. If target_cert_id is omitted, the
    Curator autonomously chooses the most appropriate certification based on
    the learner's role, history, and burnout state.

    Args:
        learner_id: e.g. 'CLN-N-001' (use the medlearn://learners resource).
        target_cert_id: optional explicit cert; omit to let the agent decide.
    """
    if learner_id not in _valid_learner_ids():
        return _err(f"Unknown learner_id '{learner_id}'. See medlearn://learners.")
    if target_cert_id and target_cert_id not in _valid_cert_ids():
        return _err(f"Unknown target_cert_id '{target_cert_id}'.")
    orch = _get_orchestrator()
    result = orch.curator.recommend(
        learner_id=learner_id, target_cert_id=target_cert_id
    )
    return _ok(result)


@mcp.tool()
def build_study_plan(learner_id: str, target_cert_id: str) -> str:
    """Build a shift-aware, burnout-scaled week-by-week study plan.

    Runs the Study Plan Generator agent.

    Args:
        learner_id: e.g. 'CLN-N-001'.
        target_cert_id: e.g. 'CCRN-2024'.
    """
    if learner_id not in _valid_learner_ids():
        return _err(f"Unknown learner_id '{learner_id}'. See medlearn://learners.")
    if target_cert_id not in _valid_cert_ids():
        return _err(f"Unknown target_cert_id '{target_cert_id}'.")
    orch = _get_orchestrator()
    result = orch.study_plan.generate(
        learner_id=learner_id, target_cert_id=target_cert_id
    )
    return _ok(result)


@mcp.tool()
def decide_engagement(learner_id: str, occasion: str) -> str:
    """Decide whether to send a study reminder, reschedule, or refuse+escalate.

    Runs the Engagement Agent — MedLearn's ethical-refusal pattern. For
    high-burnout learners it refuses to send reminders and escalates to a
    manager instead.

    Args:
        learner_id: e.g. 'CLN-P-001'.
        occasion: free-text reason for the reminder, e.g.
                  'Week 1 study reminder for BCPS-2024'.
    """
    if learner_id not in _valid_learner_ids():
        return _err(f"Unknown learner_id '{learner_id}'. See medlearn://learners.")
    if not occasion or not occasion.strip():
        return _err("occasion must be a non-empty description.")
    orch = _get_orchestrator()
    result = orch.engagement.decide(learner_id=learner_id, occasion=occasion)
    return _ok(result)


@mcp.tool()
def assess_readiness(learner_id: str, target_cert_id: str) -> str:
    """Generate practice questions and predict exam readiness.

    Runs the Assessment Agent.

    Args:
        learner_id: e.g. 'CLN-N-001'.
        target_cert_id: e.g. 'CCRN-2024'.
    """
    if learner_id not in _valid_learner_ids():
        return _err(f"Unknown learner_id '{learner_id}'. See medlearn://learners.")
    if target_cert_id not in _valid_cert_ids():
        return _err(f"Unknown target_cert_id '{target_cert_id}'.")
    orch = _get_orchestrator()
    result = orch.assessment.assess(
        learner_id=learner_id, target_cert_id=target_cert_id
    )
    return _ok(result)


@mcp.tool()
def analyze_team(team_id: str, escalation_note: Optional[str] = None) -> str:
    """Produce a team-level manager dashboard (aggregate, privacy-preserving).

    Runs the Manager Insights Agent. Optionally incorporates an escalation
    note (e.g. forwarded from a burnout-driven engagement refusal).

    Args:
        team_id: e.g. 'TEAM-ICU-NIGHT' (see medlearn://teams).
        escalation_note: optional escalation to incorporate as a top concern.
    """
    if team_id not in _valid_team_ids():
        return _err(f"Unknown team_id '{team_id}'.")
    orch = _get_orchestrator()
    result = orch.manager.analyze(team_id=team_id, escalation_note=escalation_note)
    return _ok(result)


@mcp.tool()
def run_full_journey(
    learner_id: str, target_cert_id: Optional[str] = None
) -> str:
    """Run the complete MedLearn AI pipeline end-to-end for one learner.

    Coordinates all 6 agents (Curator -> Study Plan -> Engagement -> Assessment
    -> Manager Insights when escalation fires), each reviewed by the Critic
    agent with a regeneration loop. Returns the full LearnerJourneyReport.

    Args:
        learner_id: e.g. 'CLN-N-001'.
        target_cert_id: optional; omit to let the Curator choose.
    """
    if learner_id not in _valid_learner_ids():
        return _err(f"Unknown learner_id '{learner_id}'. See medlearn://learners.")
    if target_cert_id and target_cert_id not in _valid_cert_ids():
        return _err(f"Unknown target_cert_id '{target_cert_id}'.")
    orch = _get_orchestrator()
    report = orch.run_journey(learner_id=learner_id, target_cert_id=target_cert_id)
    return _ok(report)


# ---------------------------------------------------------------------------
# Resources (for ID discovery)
# ---------------------------------------------------------------------------


@mcp.resource("medlearn://learners")
def list_learners_resource() -> str:
    """List valid learner IDs with their roles, for tool input discovery."""
    learners = load_learners().learners
    data = [
        {
            "learner_id": l.learner_id,
            "role_code": getattr(l, "role_code", None),
            "team_id": getattr(l, "team_id", None),
        }
        for l in learners
    ]
    return json.dumps(data, indent=2, default=str)


@mcp.resource("medlearn://certifications")
def list_certifications_resource() -> str:
    """List valid certification IDs, for tool input discovery."""
    certs = load_certifications().certifications
    data = [
        {"id": c.id, "name": getattr(c, "display_name", None)} for c in certs
    ]
    return json.dumps(data, indent=2, default=str)


@mcp.resource("medlearn://teams")
def list_teams_resource() -> str:
    """List valid team IDs, for the analyze_team tool."""
    teams = load_team_reports().team_reports
    data = [{"team_id": t.team_id} for t in teams]
    return json.dumps(data, indent=2, default=str)


if __name__ == "__main__":
    # stdio transport is the default for local clients like Claude Desktop.
    mcp.run()
