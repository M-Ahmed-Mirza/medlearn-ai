"""
MedLearn AI - Assessment Agent Smoke Test

Tests the Assessment Agent against three carefully chosen scenarios to
prove it generates valid questions AND predicts readiness correctly:

Scenario A — CLN-N-001 / CCRN-2024:
    Profile: practice_score_avg=72, last_assessment_outcome=Fail,
             hours_studied_last_quarter=22.
    Cert min passing score: 80.
    Expected: 'Not Ready' or 'Approaching Ready' — fail caps readiness.

Scenario B — CLN-N-002 / ACLS-2024:
    Profile: stronger candidate.
    Expected: 'Ready' or 'Approaching Ready'.

Scenario C — CLN-L-001 / BLS-2024:
    Profile: low-stakes regulatory cert, short cycle.
    Expected: 'Ready' or 'Exam Recommended' (BLS is straightforward).

Run from project root:
    python -m scripts.test_assessment
"""

from dotenv import load_dotenv

load_dotenv()  # Load .env BEFORE importing the agent

from medlearn import AssessmentAgent
from medlearn.models import AssessmentResult


def pretty_print(result: AssessmentResult) -> None:
    """Render an assessment result in a readable form."""
    print()
    print("=" * 78)

    readiness_label = {
        "Not Ready": "[RED]    Not Ready",
        "Approaching Ready": "[YELLOW] Approaching Ready",
        "Ready": "[GREEN]  Ready",
        "Exam Recommended": "[BLUE]   Exam Recommended",
    }.get(result.readiness_level, f"[?] {result.readiness_level}")

    print(f"  Learner: {result.learner_id}")
    print(f"  Target Cert: {result.target_certification_id} — {result.target_certification_name}")
    print(f"  Readiness: {readiness_label} (score: {result.readiness_score:.2f})")
    print(f"  Confidence: {result.confidence:.2f}")
    print("=" * 78)

    print("\n  RATIONALE:")
    print(f"  {result.rationale}")

    print(f"\n  RECOMMENDED NEXT STEP:")
    print(f"  -> {result.recommended_next_step}")

    if result.focus_areas:
        print(f"\n  FOCUS AREAS ({len(result.focus_areas)}):")
        for area in result.focus_areas:
            print(f"    - {area}")

    print(f"\n  PRACTICE QUESTIONS ({len(result.questions)}):")
    for q in result.questions:
        print(f"\n    {q.question_id} [{q.difficulty}] — {q.skill_tested}")
        print(f"    Q: {q.question}")
        for i, opt in enumerate(q.options):
            letter = chr(ord("A") + i)
            marker = " <-- correct" if letter == q.correct_answer else ""
            print(f"       {letter}. {opt}{marker}")
        print(f"    Explanation: {q.explanation}")

    if result.citations:
        print(f"\n  CITATIONS ({len(result.citations)}):")
        for c in result.citations:
            section = f" ({c.section})" if c.section else ""
            print(f"    - {c.source_document}{section}")

    if result.safety_flags:
        print(f"\n  SAFETY FLAGS ({len(result.safety_flags)}):")
        for flag in result.safety_flags:
            print(f"    !! {flag}")
    else:
        print("\n  Safety flags: none")


def main() -> None:
    print("=" * 78)
    print("MedLearn AI - Assessment Agent Smoke Test")
    print("=" * 78)
    print("Testing question generation + readiness prediction across 3 profiles.")

    agent = AssessmentAgent()

    test_cases = [
        (
            "CLN-N-001",
            "CCRN-2024",
            5,
            "Critical Care RN with recent Fail outcome — expect Not Ready / Approaching",
        ),
        (
            "CLN-N-002",
            "ACLS-2024",
            5,
            "Stronger RN candidate — expect Ready / Approaching",
        ),
        (
            "CLN-L-001",
            "BLS-2024",
            4,
            "Lab Tech, simple regulatory cert — expect Ready / Exam Recommended",
        ),
    ]

    for learner_id, cert_id, num_q, description in test_cases:
        print(f"\n\n>> RUNNING: {description}")
        try:
            result = agent.assess(
                learner_id=learner_id,
                target_cert_id=cert_id,
                num_questions=num_q,
            )
            pretty_print(result)
        except Exception as e:
            print(f"  FAILED: {type(e).__name__}: {e}")

    print("\n\n" + "=" * 78)
    print("Assessment Agent smoke test complete.")
    print("=" * 78)


if __name__ == "__main__":
    main()
