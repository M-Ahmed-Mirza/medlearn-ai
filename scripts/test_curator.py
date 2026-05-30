"""
MedLearn AI - Learning Path Curator Smoke Test

Runs the Curator against 3 different learner profiles to verify:
- Agent loads .env credentials
- Connects to Foundry GPT-4o
- Returns valid CuratorRecommendation JSON
- Citations, confidence scores, and alternatives populate

Run from project root:
    python scripts/test_curator.py
"""

from dotenv import load_dotenv

load_dotenv()  # Load .env BEFORE importing the agent

from medlearn import LearningPathCurator
from medlearn.models import CuratorRecommendation


def pretty_print(rec: CuratorRecommendation) -> None:
    """Render a recommendation in a readable form."""
    print()
    print("=" * 70)
    print(f"  Learner: {rec.learner_id}")
    print(f"  Recommended Cert: {rec.target_certification_id} — {rec.target_certification_name}")
    print(f"  Confidence: {rec.confidence:.2f}")
    print(f"  Study Hours: {rec.recommended_study_hours}")
    print(f"  Prerequisites: {rec.prerequisites_status}")
    print("=" * 70)

    print("\n  RATIONALE:")
    print(f"  {rec.rationale}")

    print(f"\n  SKILLS TO ACQUIRE ({len(rec.skills_to_acquire)}):")
    for skill in rec.skills_to_acquire:
        print(f"    - {skill}")

    if rec.citations:
        print(f"\n  CITATIONS ({len(rec.citations)}):")
        for c in rec.citations:
            section = f" ({c.section})" if c.section else ""
            print(f"    - {c.source_document}{section}")

    if rec.alternatives_considered:
        print(f"\n  ALTERNATIVES CONSIDERED ({len(rec.alternatives_considered)}):")
        for alt in rec.alternatives_considered:
            print(f"    - {alt.option}")
            print(f"      Rejected because: {alt.rejected_because}")

    if rec.safety_flags:
        print(f"\n  SAFETY FLAGS ({len(rec.safety_flags)}):")
        for flag in rec.safety_flags:
            print(f"    !! {flag}")
    else:
        print("\n  Safety flags: none")


def main() -> None:
    print("=" * 70)
    print("MedLearn AI - Learning Path Curator Smoke Test")
    print("=" * 70)

    curator = LearningPathCurator()

    # Test against 3 different roles to verify agent generalizes
    test_cases = [
        ("CLN-N-001", "CCRN-2024", "Critical Care RN aiming for CCRN"),
        ("CLN-P-001", None, "Hospital Pharmacist (no specific target)"),
        ("CLN-L-001", None, "Medical Lab Tech (no specific target)"),
    ]

    for learner_id, target, description in test_cases:
        print(f"\n\n>> RUNNING: {description}")
        try:
            rec = curator.recommend(learner_id=learner_id, target_cert_id=target)
            pretty_print(rec)
        except Exception as e:
            print(f"  FAILED: {type(e).__name__}: {e}")

    print("\n\n" + "=" * 70)
    print("Curator smoke test complete.")
    print("=" * 70)


if __name__ == "__main__":
    main()
