"""
Smoke test for MedLearn AI data layer.

Confirms that:
- All Pydantic schemas import cleanly
- All synthetic JSON files parse and validate
- Every record passes the synthetic-data guardrails
- Catalogs return the expected counts

Run with:
    python -m tests.test_data_loading
"""

from agents.data_loader import (
    load_certifications,
    load_learners,
    load_team_reports,
    load_work_signals,
)


def test_load_learners() -> None:
    catalog = load_learners()
    assert len(catalog.learners) == 6, f"Expected 6 learners, got {len(catalog.learners)}"
    role_codes = {learner.role_code for learner in catalog.learners}
    assert len(role_codes) == 3, "Expected 3 distinct role codes"
    print(f"  PASS: {len(catalog.learners)} learners across {len(role_codes)} roles")


def test_load_certifications() -> None:
    catalog = load_certifications()
    assert len(catalog.certifications) == 8, (
        f"Expected 8 certifications, got {len(catalog.certifications)}"
    )
    cert_ids = [cert.id for cert in catalog.certifications]
    assert "CCRN-2024" in cert_ids, "Expected CCRN-2024 in the catalog"
    assert "HIPAA-ANNUAL-2026" in cert_ids, "Expected HIPAA-ANNUAL-2026 in the catalog"
    print(f"  PASS: {len(catalog.certifications)} certifications validated")


def test_load_work_signals() -> None:
    catalog = load_work_signals()
    assert len(catalog.work_signals) == 6, (
        f"Expected 6 work signals (one per learner), got {len(catalog.work_signals)}"
    )
    print(f"  PASS: {len(catalog.work_signals)} work signals validated")


def test_load_team_reports() -> None:
    catalog = load_team_reports()
    assert len(catalog.team_reports) == 6, (
        f"Expected 6 team reports, got {len(catalog.team_reports)}"
    )
    assert len(catalog.department_rollup) == 3, (
        f"Expected 3 department rollups, got {len(catalog.department_rollup)}"
    )
    print(
        f"  PASS: {len(catalog.team_reports)} team reports + "
        f"{len(catalog.department_rollup)} department rollups validated"
    )


def test_cross_references() -> None:
    """Spot-check that learner_ids in work_signals exist in the learners catalog."""
    learners = load_learners()
    work_signals = load_work_signals()
    learner_ids = {learner.learner_id for learner in learners.learners}
    signal_learner_ids = {signal.learner_id for signal in work_signals.work_signals}
    missing = signal_learner_ids - learner_ids
    assert not missing, f"Work signals reference unknown learners: {missing}"
    print(f"  PASS: all {len(signal_learner_ids)} work-signal references resolve to known learners")


def main() -> None:
    print("=" * 60)
    print("MedLearn AI - Data Layer Smoke Test")
    print("=" * 60)

    tests = [
        ("Loading learners", test_load_learners),
        ("Loading certifications", test_load_certifications),
        ("Loading work signals", test_load_work_signals),
        ("Loading team reports", test_load_team_reports),
        ("Cross-reference integrity", test_cross_references),
    ]

    for name, test_fn in tests:
        print(f"\n>> {name}")
        test_fn()

    print("\n" + "=" * 60)
    print("All data-layer tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
