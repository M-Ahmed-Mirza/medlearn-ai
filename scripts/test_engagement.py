"""
MedLearn AI - Engagement Agent Smoke Test

Tests the Engagement Agent against three carefully chosen scenarios that
together prove the agent makes ethical, burnout-aware decisions:

Scenario A — Low burnout learner (CLN-L-001):
    Expected action: SEND_REMINDER (safe to engage).

Scenario B — Moderate burnout learner (CLN-N-001):
    Expected action: SEND_REMINDER with gentle tone (extra care).

Scenario C — HIGH burnout + on-call learner (CLN-P-001):
    Expected action: REFUSE_AND_ESCALATE (duty-of-care refusal).
    This is the V1.5 ethical-refusal differentiator firing.

Run from project root:
    python -m scripts.test_engagement
"""

from dotenv import load_dotenv

load_dotenv()  # Load .env BEFORE importing the agent

from medlearn import EngagementAgent
from medlearn.models import EngagementDecision


def pretty_print(decision: EngagementDecision) -> None:
    """Render an engagement decision in a readable form."""
    print()
    print("=" * 78)

    action_label = {
        "SEND_REMINDER": "[GREEN]  SEND_REMINDER",
        "RESCHEDULE": "[YELLOW] RESCHEDULE",
        "REFUSE_AND_ESCALATE": "[RED]    REFUSE_AND_ESCALATE",
    }.get(decision.action, f"[?] {decision.action}")

    print(f"  Learner: {decision.learner_id}")
    print(f"  Decision: {action_label}")
    print(f"  Confidence: {decision.confidence:.2f}")
    print("=" * 78)

    print("\n  RATIONALE:")
    print(f"  {decision.rationale}")

    if decision.action == "SEND_REMINDER":
        print(f"\n  MESSAGE TO LEARNER:")
        print(f"  \"{decision.message_to_learner}\"")
        if decision.proposed_time:
            print(f"\n  SCHEDULED FOR: {decision.proposed_time}")
    elif decision.action == "RESCHEDULE":
        print(f"\n  MESSAGE TO LEARNER:")
        print(f"  \"{decision.message_to_learner}\"")
        print(f"\n  RESCHEDULED FOR: {decision.proposed_time}")
    elif decision.action == "REFUSE_AND_ESCALATE":
        print(f"\n  NO MESSAGE SENT TO LEARNER (ethical refusal)")
        print(f"\n  ESCALATION TO MANAGER INSIGHTS:")
        print(f"  \"{decision.escalation_note}\"")

    if decision.citations:
        print(f"\n  CITATIONS ({len(decision.citations)}):")
        for c in decision.citations:
            section = f" ({c.section})" if c.section else ""
            print(f"    - {c.source_document}{section}")

    if decision.safety_flags:
        print(f"\n  SAFETY FLAGS ({len(decision.safety_flags)}):")
        for flag in decision.safety_flags:
            print(f"    !! {flag}")
    else:
        print("\n  Safety flags: none")


def main() -> None:
    print("=" * 78)
    print("MedLearn AI - Engagement Agent Smoke Test")
    print("=" * 78)
    print("Testing burnout-aware ethical-refusal logic across 3 risk profiles.")

    agent = EngagementAgent()

    # Carefully ordered to demonstrate escalating burnout response
    test_cases = [
        (
            "CLN-L-001",
            "Weekly BLS-2024 study reminder, Week 2 of 3 — practice CPR module due",
            "[LOW burnout] Lab Tech with low workload — should SEND_REMINDER",
        ),
        (
            "CLN-N-001",
            "CCRN-2024 study reminder, Week 1 of 6 — first hemodynamics session due",
            "[MODERATE burnout] Critical Care RN with recent assessment failure — gentle SEND or RESCHEDULE",
        ),
        (
            "CLN-P-001",
            "BCPS-2024 study reminder, Week 1 of 10 — pharmacokinetics module due",
            "[HIGH burnout + on-call] Pharmacist — should REFUSE_AND_ESCALATE",
        ),
    ]

    for learner_id, occasion, description in test_cases:
        print(f"\n\n>> RUNNING: {description}")
        try:
            decision = agent.decide(learner_id=learner_id, occasion=occasion)
            pretty_print(decision)
        except Exception as e:
            print(f"  FAILED: {type(e).__name__}: {e}")

    print("\n\n" + "=" * 78)
    print("Engagement Agent smoke test complete.")
    print("=" * 78)


if __name__ == "__main__":
    main()
