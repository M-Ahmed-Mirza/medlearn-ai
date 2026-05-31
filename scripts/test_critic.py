"""
MedLearn AI - Critic Agent Smoke Test (V1.5 self-correction loop)

This is the most important test in the project — it proves the Critic Agent
can review real outputs from other agents and catch problems.

Workflow:
    1. Run Learning Path Curator on a real learner.
    2. Pass its output to Critic. Should be APPROVED (Curator is well-tested).
    3. Run Engagement Agent on a HIGH-burnout learner (refuse_and_escalate case).
    4. Pass its output to Critic. Should be APPROVED — refusal pattern was
       correct.
    5. Run Manager Insights with an escalation.
    6. Pass its output to Critic. Should catch any drift.

This demonstrates the V1.5 self-correction loop in action and is the most
demoable piece of MedLearn AI.

Run from project root:
    python -m scripts.test_critic
"""

from dotenv import load_dotenv

load_dotenv()

from medlearn import (
    CriticAgent,
    EngagementAgent,
    LearningPathCurator,
    ManagerInsightsAgent,
)
from medlearn.models import CriticVerdict


def pretty_print_verdict(verdict: CriticVerdict) -> None:
    """Render a Critic verdict in a readable form."""
    verdict_marker = {
        "APPROVED": "[GREEN]  APPROVED",
        "NEEDS_REVISION": "[YELLOW] NEEDS_REVISION",
        "REJECTED": "[RED]    REJECTED",
    }.get(verdict.verdict, f"[?] {verdict.verdict}")

    print()
    print("=" * 78)
    print(f"  Reviewed Agent: {verdict.reviewed_agent}")
    print(f"  Verdict: {verdict_marker}")
    print(f"  Quality Score: {verdict.overall_quality_score:.2f}")
    print(f"  Critic Confidence: {verdict.confidence:.2f}")
    print("=" * 78)

    print("\n  RATIONALE:")
    print(f"  {verdict.rationale}")

    if verdict.issues:
        print(f"\n  ISSUES FOUND ({len(verdict.issues)}):")
        sev_marker = {"Blocker": "[!!]", "Major": "[! ]", "Minor": "[. ]"}
        for issue in verdict.issues:
            marker = sev_marker.get(issue.severity, "[?]")
            print(f"    {marker} {issue.severity} on `{issue.field}`")
            print(f"         Problem: {issue.problem}")
            print(f"         Fix:     {issue.suggested_fix}")
    else:
        print("\n  No issues found.")

    if verdict.regeneration_prompt:
        print("\n  REGENERATION PROMPT (for original agent):")
        print(f"  \"{verdict.regeneration_prompt}\"")


def main() -> None:
    print("=" * 78)
    print("MedLearn AI - Critic Agent Smoke Test (V1.5 self-correction loop)")
    print("=" * 78)
    print("Generating real outputs from other agents, then having Critic review them.\n")

    critic = CriticAgent()

    # ----- Scenario 1: Curator output -----
    print("\n>> SCENARIO 1: Critic reviews LearningPathCurator output")
    print("   (1a) Running Curator on CLN-N-001...")
    curator = LearningPathCurator()
    curator_output = curator.recommend(learner_id="CLN-N-001", target_cert_id="CCRN-2024")
    print(f"   (1b) Curator recommended: {curator_output.target_certification_id} "
          f"(confidence {curator_output.confidence:.2f})")
    print("   (1c) Critic reviewing...")
    verdict_1 = critic.review("LearningPathCurator", curator_output)
    pretty_print_verdict(verdict_1)

    # ----- Scenario 2: Engagement (high-burnout refusal case) -----
    print("\n\n>> SCENARIO 2: Critic reviews EngagementAgent output (refusal case)")
    print("   (2a) Running Engagement on CLN-P-001 (HIGH burnout, on-call)...")
    engagement = EngagementAgent()
    engagement_output = engagement.decide(
        learner_id="CLN-P-001",
        occasion="BCPS-2024 Week 1 study reminder",
    )
    print(f"   (2b) Engagement decision: {engagement_output.action}")
    print("   (2c) Critic reviewing...")
    verdict_2 = critic.review("EngagementAgent", engagement_output)
    pretty_print_verdict(verdict_2)

    # ----- Scenario 3: Manager Insights with escalation -----
    print("\n\n>> SCENARIO 3: Critic reviews ManagerInsightsAgent output")
    print("   (3a) Running Manager Insights on TEAM-ICU-NIGHT with escalation...")
    manager = ManagerInsightsAgent()
    manager_output = manager.analyze(
        team_id="TEAM-ICU-NIGHT",
        escalation_note=(
            "Engagement Agent refused to send a study reminder this morning. "
            "Learner at high burnout, workload 85, on-call. "
            "Recommend immediate workload review."
        ),
    )
    print(f"   (3b) Manager Insights status: {manager_output.overall_health_status}")
    print("   (3c) Critic reviewing...")
    verdict_3 = critic.review("ManagerInsightsAgent", manager_output)
    pretty_print_verdict(verdict_3)

    # Summary
    print("\n\n" + "=" * 78)
    print("CRITIC SUMMARY")
    print("=" * 78)
    verdicts = [verdict_1, verdict_2, verdict_3]
    names = ["Curator", "Engagement (refusal)", "Manager Insights"]
    for name, v in zip(names, verdicts):
        print(f"  {name:25s} -> {v.verdict:20s} (quality {v.overall_quality_score:.2f})")

    approved = sum(1 for v in verdicts if v.verdict == "APPROVED")
    revisions = sum(1 for v in verdicts if v.verdict == "NEEDS_REVISION")
    rejected = sum(1 for v in verdicts if v.verdict == "REJECTED")
    print(f"\n  Final: {approved} APPROVED, {revisions} NEEDS_REVISION, {rejected} REJECTED")

    print("\n" + "=" * 78)
    print("Critic Agent smoke test complete.")
    print("=" * 78)


if __name__ == "__main__":
    main()
