"""
MedLearn AI - Manager Insights Agent Smoke Test

Tests the Manager Insights Agent against three scenarios spanning team
health levels and the escalation-handling path:

Scenario A — TEAM-LAB-CHEM (healthy):
    96% compliance, 0 high burnout, 78% pass rate.
    Expected overall_health_status: 'Healthy' or 'Some concerns'.

Scenario B — TEAM-PHARM-A (concerning):
    50% of team at HIGH burnout (3 of 6 members).
    Expected overall_health_status: 'Concerning' or 'Critical — immediate action'.
    Expected severity escalation across top_concerns.

Scenario C — TEAM-ICU-NIGHT + Engagement Agent escalation:
    Simulates a forwarded REFUSE_AND_ESCALATE from the Engagement Agent.
    The agent should incorporate the escalation into top_concerns.

Run from project root:
    python -m scripts.test_manager_insights
"""

from dotenv import load_dotenv

load_dotenv()  # Load .env BEFORE importing the agent

from medlearn import ManagerInsightsAgent
from medlearn.models import ManagerInsight


def pretty_print(insight: ManagerInsight) -> None:
    """Render a manager insight in a readable form."""
    print()
    print("=" * 78)

    health_label = {
        "Healthy": "[GREEN]  Healthy",
        "Some concerns": "[YELLOW] Some concerns",
        "Concerning": "[ORANGE] Concerning",
        "Critical — immediate action": "[RED]    Critical — immediate action",
    }.get(insight.overall_health_status, f"[?] {insight.overall_health_status}")

    print(f"  Team: {insight.team_id} — {insight.team_name}")
    print(f"  Team Size: {insight.team_size}")
    print(f"  Status: {health_label}")
    print(f"  Confidence: {insight.confidence:.2f}")
    print("=" * 78)

    print("\n  COMPLIANCE:")
    print(f"  {insight.compliance_summary}")

    print("\n  BURNOUT PATTERN:")
    print(f"  {insight.burnout_pattern}")

    print("\n  CERTIFICATION PIPELINE:")
    print(f"  {insight.certification_pipeline}")

    print("\n  RATIONALE:")
    print(f"  {insight.rationale}")

    print(f"\n  TOP CONCERNS ({len(insight.top_concerns)}, ordered most severe first):")
    severity_marker = {
        "Critical": "[!!]",
        "High": "[! ]",
        "Moderate": "[~ ]",
        "Low": "[. ]",
    }
    for c in insight.top_concerns:
        marker = severity_marker.get(c.severity, "[?]")
        print(f"    {marker} {c.severity}: {c.concern}")
        print(f"         Affected: {c.affected_count} members")
        print(f"         Action: {c.recommended_intervention}")

    print(f"\n  RECOMMENDED ACTIONS THIS WEEK ({len(insight.recommended_actions)}):")
    for i, action in enumerate(insight.recommended_actions, start=1):
        print(f"    {i}. {action}")

    if insight.citations:
        print(f"\n  CITATIONS ({len(insight.citations)}):")
        for c in insight.citations:
            section = f" ({c.section})" if c.section else ""
            print(f"    - {c.source_document}{section}")

    if insight.safety_flags:
        print(f"\n  SAFETY FLAGS ({len(insight.safety_flags)}):")
        for flag in insight.safety_flags:
            print(f"    !! {flag}")
    else:
        print("\n  Safety flags: none")


def main() -> None:
    print("=" * 78)
    print("MedLearn AI - Manager Insights Agent Smoke Test")
    print("=" * 78)
    print("Testing team-level insights + escalation handling across 3 profiles.")

    agent = ManagerInsightsAgent()

    test_cases = [
        (
            "TEAM-LAB-CHEM",
            None,
            "Healthy team (96% compliance, 0 high burnout) — expect 'Healthy' / 'Some concerns'",
        ),
        (
            "TEAM-PHARM-A",
            None,
            "Concerning team (3 of 6 members at HIGH burnout) — expect 'Concerning' / 'Critical'",
        ),
        (
            "TEAM-ICU-NIGHT",
            (
                "Engagement Agent refused to send a study reminder this morning. "
                "Learner has high burnout risk indicator, workload score of 85, "
                "and is currently on-call. Recommend immediate workload review."
            ),
            "Mixed team + active escalation from Engagement Agent",
        ),
    ]

    for team_id, escalation, description in test_cases:
        print(f"\n\n>> RUNNING: {description}")
        try:
            insight = agent.analyze(team_id=team_id, escalation_note=escalation)
            pretty_print(insight)
        except Exception as e:
            print(f"  FAILED: {type(e).__name__}: {e}")

    print("\n\n" + "=" * 78)
    print("Manager Insights Agent smoke test complete.")
    print("=" * 78)


if __name__ == "__main__":
    main()
