"""
MedLearn AI - End-to-End Orchestration Smoke Test (Phase 3)

This is THE big test. It runs the complete MedLearn AI pipeline:

    Curator -> [Critic] -> StudyPlan -> [Critic] -> Engagement -> [Critic]
                                                       |
                                                       v (if escalate)
                                            Manager Insights -> [Critic]
                                            +
                          Assessment -> [Critic]
                                                       |
                                                       v
                                          LearnerJourneyReport

Two scenarios:

Scenario A (normal path) — CLN-N-001 (Critical Care RN, moderate burnout):
    Curator picks CCRN, Study Plan builds 5-6 weeks, Engagement sends gentle
    or reschedules reminder, Assessment generates questions + readiness.
    NO escalation, Manager Insights skipped. All Critic verdicts APPROVED.

Scenario B (ethical escalation) — CLN-P-001 (Pharmacist, HIGH burnout, on-call):
    Curator picks BCPS, Study Plan caps intensity, Engagement REFUSES and
    escalates, Manager Insights kicks in with the escalation incorporated.
    Critic approves all. This proves the ethical loop closes end-to-end.

Run from project root:
    python -m scripts.test_orchestration
"""

from dotenv import load_dotenv

load_dotenv()  # Load .env BEFORE importing the agents

from medlearn import Orchestrator
from medlearn.models import LearnerJourneyReport


def print_report(report: LearnerJourneyReport) -> None:
    """Pretty-print a complete journey report."""
    print()
    print("=" * 78)
    print(f"  FINAL JOURNEY REPORT — {report.learner_id}")
    print("=" * 78)
    print(f"  Target Cert: {report.target_certification_id}")
    print(f"  Pipeline Status: {report.pipeline_status.upper()}")
    print(f"  Escalation Triggered: {report.escalation_triggered}")
    print(f"  Total Critic Regenerations: {report.total_critic_regenerations}")
    print("=" * 78)

    # Stage summaries
    stages = [
        ("Stage 1 - Curator", report.curator_review,
         f"Recommended {report.curator_recommendation.target_certification_id} "
         f"(conf {report.curator_recommendation.confidence:.2f})"),
        ("Stage 2 - Study Plan", report.study_plan_review,
         f"{report.study_plan.total_weeks}wk plan / "
         f"{report.study_plan.total_study_hours:.0f}h total "
         f"({report.study_plan.schedule_feasibility})"),
        ("Stage 3 - Engagement", report.engagement_review,
         f"Action: {report.engagement_decision.action} "
         f"(conf {report.engagement_decision.confidence:.2f})"),
        ("Stage 4 - Assessment", report.assessment_review,
         f"Readiness: {report.assessment_result.readiness_level} "
         f"({report.assessment_result.readiness_score:.2f}) — "
         f"{len(report.assessment_result.questions)} questions"),
    ]

    if report.manager_insight and report.manager_review:
        stages.append((
            "Stage 5 - Manager Insights",
            report.manager_review,
            f"Status: {report.manager_insight.overall_health_status} — "
            f"{len(report.manager_insight.top_concerns)} concerns",
        ))

    print("\n  PIPELINE STAGES:")
    for name, review, detail in stages:
        marker = {
            "APPROVED": "[GREEN] APPROVED",
            "NEEDS_REVISION": "[YELLOW] NEEDS_REVISION (regenerated)",
            "REJECTED": "[RED] REJECTED",
        }.get(review.verdict, review.verdict)
        regen = " [REGENERATED]" if review.regenerated else ""
        print(f"\n  {name}:")
        print(f"    Critic: {marker} (quality {review.quality_score:.2f}){regen}")
        print(f"    Output: {detail}")

    if report.engagement_decision.action == "REFUSE_AND_ESCALATE":
        print(f"\n  ETHICAL REFUSAL EVIDENCE:")
        print(f"    Escalation note: \"{report.engagement_decision.escalation_note}\"")

    if report.manager_insight:
        print(f"\n  MANAGER DASHBOARD HIGHLIGHTS:")
        for concern in report.manager_insight.top_concerns[:3]:
            print(f"    [{concern.severity}] {concern.concern}")


def main() -> None:
    print("=" * 78)
    print("MedLearn AI - End-to-End Orchestration Smoke Test (Phase 3)")
    print("=" * 78)
    print("Running the complete 6-agent pipeline on 2 distinct scenarios.\n")

    orch = Orchestrator(verbose=True)

    # ----- Scenario A: Normal path -----
    print("\n>> SCENARIO A: CLN-N-001 (Moderate burnout RN -> CCRN)")
    print("   Expected: full pipeline runs, all approved, no escalation\n")
    try:
        report_a = orch.run_journey(
            learner_id="CLN-N-001", target_cert_id="CCRN-2024"
        )
        print_report(report_a)
    except Exception as exc:
        print(f"  FAILED: {type(exc).__name__}: {exc}")
        return

    # ----- Scenario B: Escalation path -----
    print("\n\n" + "=" * 78)
    print(">> SCENARIO B: CLN-P-001 (HIGH burnout pharmacist -> BCPS)")
    print("   Expected: Engagement REFUSES, Manager Insights kicks in\n")
    try:
        report_b = orch.run_journey(
            learner_id="CLN-P-001", target_cert_id="BCPS-2024"
        )
        print_report(report_b)
    except Exception as exc:
        print(f"  FAILED: {type(exc).__name__}: {exc}")
        return

    # ----- Final summary -----
    print("\n\n" + "=" * 78)
    print("OVERALL PIPELINE SUMMARY")
    print("=" * 78)
    print(f"  Scenario A ({report_a.learner_id}): {report_a.pipeline_status} "
          f"(escalation: {report_a.escalation_triggered}, regens: {report_a.total_critic_regenerations})")
    print(f"  Scenario B ({report_b.learner_id}): {report_b.pipeline_status} "
          f"(escalation: {report_b.escalation_triggered}, regens: {report_b.total_critic_regenerations})")

    if (report_b.escalation_triggered and report_b.manager_insight is not None):
        print("\n  ETHICAL LOOP CLOSED END-TO-END:")
        print("    Engagement refused -> Manager Insights received escalation -> reviewed by Critic")
        print("    This is the V1.5 differentiator firing across the full system.")

    print("\n" + "=" * 78)
    print("End-to-end orchestration test complete.")
    print("=" * 78)


if __name__ == "__main__":
    main()
