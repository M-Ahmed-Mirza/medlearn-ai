"""
MedLearn AI - Study Plan Generator Smoke Test

Runs the Study Plan Generator against 3 learners to verify:
- Agent reads work signals (shift pattern, burnout, focus hours)
- Generates valid StudyPlan with week-by-week schedule
- Adjusts intensity based on burnout risk
- Raises safety flags when appropriate

Run from project root:
    python -m scripts.test_study_plan
"""

from dotenv import load_dotenv

load_dotenv()  # Load .env BEFORE importing the agent

from medlearn import StudyPlanGenerator
from medlearn.models import StudyPlan


def pretty_print(plan: StudyPlan) -> None:
    """Render a study plan in a readable form."""
    print()
    print("=" * 78)
    print(f"  Learner: {plan.learner_id}")
    print(f"  Target Cert: {plan.target_certification_id} — {plan.target_certification_name}")
    print(f"  Plan Length: {plan.total_weeks} weeks ({plan.total_study_hours:.1f} total hours)")
    print(f"  Weekly Target: {plan.weekly_hour_target:.1f} hours/week")
    print(f"  Study Window: {plan.preferred_study_window}")
    print(f"  Feasibility: {plan.schedule_feasibility}")
    print(f"  Confidence: {plan.confidence:.2f}")
    print("=" * 78)

    print("\n  RATIONALE:")
    print(f"  {plan.rationale}")

    print(f"\n  WEEKLY SCHEDULE ({len(plan.weeks)} weeks):")
    for week in plan.weeks:
        milestone = f"  [MILESTONE: {week.milestone}]" if week.milestone else ""
        print(
            f"    Week {week.week_number:2d}: "
            f"{week.hours_allocated:4.1f}h across {week.sessions_per_week} sessions"
            f"{milestone}"
        )
        print(f"             Topics: {', '.join(week.focus_topics)}")

    if plan.citations:
        print(f"\n  CITATIONS ({len(plan.citations)}):")
        for c in plan.citations:
            section = f" ({c.section})" if c.section else ""
            print(f"    - {c.source_document}{section}")

    if plan.safety_flags:
        print(f"\n  SAFETY FLAGS ({len(plan.safety_flags)}):")
        for flag in plan.safety_flags:
            print(f"    !! {flag}")
    else:
        print("\n  Safety flags: none")


def main() -> None:
    print("=" * 78)
    print("MedLearn AI - Study Plan Generator Smoke Test")
    print("=" * 78)

    generator = StudyPlanGenerator()

    # Cases spanning different burnout levels + cert sizes
    test_cases = [
        ("CLN-N-001", "CCRN-2024", "Critical Care RN -> CCRN (big cert, recent fail)"),
        ("CLN-P-001", "BCPS-2024", "Hospital Pharmacist -> BCPS (large cert)"),
        ("CLN-L-001", "BLS-2024", "Medical Lab Tech -> BLS (small cert, fast turnaround)"),
    ]

    for learner_id, cert_id, description in test_cases:
        print(f"\n\n>> RUNNING: {description}")
        try:
            plan = generator.generate(learner_id=learner_id, target_cert_id=cert_id)
            pretty_print(plan)
        except Exception as e:
            print(f"  FAILED: {type(e).__name__}: {e}")

    print("\n\n" + "=" * 78)
    print("Study Plan Generator smoke test complete.")
    print("=" * 78)


if __name__ == "__main__":
    main()
