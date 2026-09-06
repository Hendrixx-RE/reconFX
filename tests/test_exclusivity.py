"""PLAN.md §3.3 / Phase 2 acceptance tests, exercised here so Phase 3 can
rely on the guarantee while Phase 2's own suite is still being written."""

from decimal import Decimal

from engine.decomposition import DecompositionState


def test_exclusivity_blocks_double_counting():
    s = DecompositionState(
        Decimal("44000"), Decimal("500"), amount_lookup={"GL-2026-0307": Decimal("310000")}
    )
    s.test_hypothesis("F1", "TIMING_UNBILLED", ["GL-2026-0307"], [])
    r = s.test_hypothesis("F2", "MISCLASSIFICATION", ["GL-2026-0307"], [])
    assert r.accepted is False
    assert r.rejection_reason == "TRANSACTION_SET_OVERLAP"
    assert "GL-2026-0307" in r.conflicting_ids


def test_materiality_gate():
    s = DecompositionState(
        Decimal("5000"), Decimal("500"), amount_lookup={"GL-2026-0309": Decimal("340")}
    )
    r = s.test_hypothesis("H3", "FX_REVALUATION", ["GL-2026-0309"], [])
    assert r.accepted is False
    assert r.rejection_reason == "BELOW_MATERIALITY"
    assert s.residual == Decimal("5000")


def test_full_act_two_run_without_llm():
    s = DecompositionState(
        Decimal("44000"),
        Decimal("500"),
        amount_lookup={"GL-2026-0307": Decimal("310000"), "GL-2026-0306": Decimal("80000")},
    )
    s.test_hypothesis("F1", "TIMING_UNBILLED", ["GL-2026-0307"], [])
    assert s.residual == Decimal("13000")
    s.test_hypothesis("F2", "APPROVED_EXCLUSION", ["GL-2026-0306"], [])
    assert s.residual == Decimal("5000")


def test_over_attribution_is_rejected():
    s = DecompositionState(
        Decimal("5000"), Decimal("500"), amount_lookup={"GL-X": Decimal("140000")}
    )
    r = s.test_hypothesis("F4", "MISCLASSIFICATION", ["GL-X"], [])
    assert r.accepted is False
    assert r.rejection_reason == "OVER_ATTRIBUTION"
    assert s.residual == Decimal("5000")
