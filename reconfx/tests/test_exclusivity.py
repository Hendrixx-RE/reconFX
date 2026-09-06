"""Tests for exclusivity logic, materiality gating, and termination.

README Section 3.3: Non-overlap constraint (the audit guarantee).
"test_hypothesis() rejects any factor whose transaction set intersects an
already-accepted set, and returns the offending doc IDs."

README Section 3.5: Materiality gate.
"if abs(F_i) < materiality_threshold: reject_hypothesis(F_i, reason='below_materiality')"

README Section 3.6: Termination.
"if abs(rho_k) < materiality_threshold:   -> FULLY_EXPLAINED, terminate
 elif hypotheses_exhausted:              -> ESCALATE with residual and required-evidence list
 elif step_count > MAX_STEPS (12):       -> ESCALATE (loop guard)"
"""

import sys
from pathlib import Path
import pytest

# Ensure reconfx package and parent repo root are on sys.path for robust imports
_tests_dir = Path(__file__).resolve().parent
_reconfx_dir = _tests_dir.parent
_repo_root = _reconfx_dir.parent

for p in (_reconfx_dir, _repo_root):
    p_str = str(p)
    if p_str not in sys.path:
        sys.path.insert(0, p_str)

try:
    from engine.decomposition import (
        ALPHA_BY_CLASSIFICATION,
        ExclusivityError,
        TerminationStatus,
        check_exclusivity,
        check_termination,
        compute_residual,
        passes_materiality_gate,
        quantify_factor,
    )
except ImportError:
    from reconfx.engine.decomposition import (
        ALPHA_BY_CLASSIFICATION,
        ExclusivityError,
        TerminationStatus,
        check_exclusivity,
        check_termination,
        compute_residual,
        passes_materiality_gate,
        quantify_factor,
    )


# ---------------------------------------------------------------------------
# Helper utilities for flexible contract assertions
# ---------------------------------------------------------------------------

def _extract_offending_ids(exc: ExclusivityError) -> set[str]:
    """Extract offending IDs from ExclusivityError whether exposed via attributes or args."""
    for attr in ("offending_ids", "conflicts", "intersection", "conflicting_ids"):
        val = getattr(exc, attr, None)
        if val is not None:
            if isinstance(val, (set, list, tuple)):
                return {str(x) for x in val}
            return {str(val)}

    if exc.args:
        first_arg = exc.args[0]
        if isinstance(first_arg, (set, list, tuple)):
            return {str(x) for x in first_arg}
        elif isinstance(first_arg, str):
            return {first_arg}

    return set()


def _matches_status(actual: str, expected_constant, expected_str: str) -> bool:
    """Verify termination status matches constant or canonical string representation."""
    return (
        actual == expected_constant
        or actual == expected_str
        or str(actual) == expected_str
        or getattr(actual, "value", None) == expected_str
    )


# ---------------------------------------------------------------------------
# Exclusivity Tests (§3.3 Non-overlap constraint)
# ---------------------------------------------------------------------------

def test_check_exclusivity_empty_accepted_sets():
    """Accepting a new set when accepted_id_sets is empty must succeed."""
    new_ids = {"GL-2026-0301"}
    accepted_id_sets = []
    # Should not raise
    assert check_exclusivity(new_ids, accepted_id_sets) is None


def test_check_exclusivity_empty_new_ids():
    """Empty new_ids set has no intersection with any accepted sets and must succeed."""
    new_ids = set()
    accepted_id_sets = [{"GL-2026-0301"}, {"GL-2026-0302"}]
    assert check_exclusivity(new_ids, accepted_id_sets) is None


def test_check_exclusivity_disjoint_sets_succeeds():
    """Accepting new IDs strictly disjoint from all accepted sets must succeed."""
    accepted_id_sets = [
        {"GL-2026-0301", "GL-2026-0302"},
        {"GL-2026-0303"},
    ]
    new_ids = {"GL-2026-0304", "GL-2026-0306"}
    assert check_exclusivity(new_ids, accepted_id_sets) is None


def test_check_exclusivity_exact_duplicate_raises_exclusivity_error():
    """Attempting to accept an already-accepted transaction ID raises ExclusivityError
    with the offending ID listed.
    """
    accepted_id_sets = [{"GL-2026-0307"}]
    new_ids = {"GL-2026-0307"}

    with pytest.raises(ExclusivityError) as exc_info:
        check_exclusivity(new_ids, accepted_id_sets)

    err = exc_info.value
    offending = _extract_offending_ids(err)
    assert "GL-2026-0307" in offending or "GL-2026-0307" in str(err)


def test_check_exclusivity_partial_overlap_raises_with_correct_offending_ids():
    """When a new hypothesis shares even a single ID with accepted sets,
    ExclusivityError is raised listing the specific conflicting ID.
    """
    accepted_id_sets = [
        {"TX-100", "TX-200"},
        {"TX-300"},
    ]
    new_ids = {"TX-200", "TX-400"}  # TX-200 is overlapping, TX-400 is not

    with pytest.raises(ExclusivityError) as exc_info:
        check_exclusivity(new_ids, accepted_id_sets)

    err = exc_info.value
    offending = _extract_offending_ids(err)
    assert "TX-200" in offending or "TX-200" in str(err)
    # The non-offending ID TX-400 should not be reported as offending
    if offending:
        assert "TX-400" not in offending


def test_check_exclusivity_multiple_conflicts_across_different_accepted_sets():
    """Conflicting IDs across multiple accepted sets must all be detected and reported."""
    accepted_id_sets = [
        {"TX-100", "TX-101"},
        {"TX-200", "TX-201"},
    ]
    new_ids = {"TX-100", "TX-201", "TX-999"}

    with pytest.raises(ExclusivityError) as exc_info:
        check_exclusivity(new_ids, accepted_id_sets)

    err = exc_info.value
    offending = _extract_offending_ids(err)
    assert ("TX-100" in offending and "TX-201" in offending) or (
        "TX-100" in str(err) and "TX-201" in str(err)
    )
    if offending:
        assert "TX-999" not in offending


# ---------------------------------------------------------------------------
# Materiality Gate Tests (§3.5 Materiality gate)
# ---------------------------------------------------------------------------

def test_passes_materiality_gate_above_threshold():
    """Factors with abs(factor) >= materiality_threshold must pass the gate."""
    threshold = 500.0
    assert passes_materiality_gate(500.01, threshold) is True
    assert passes_materiality_gate(31000.0, threshold) is True
    assert passes_materiality_gate(8000.0, threshold) is True


def test_passes_materiality_gate_exact_threshold():
    """A factor exactly equal to the materiality threshold must pass."""
    assert passes_materiality_gate(500.0, 500.0) is True


def test_passes_materiality_gate_below_threshold():
    """Factors with abs(factor) < materiality_threshold must be rejected."""
    threshold = 500.0
    assert passes_materiality_gate(499.99, threshold) is False
    assert passes_materiality_gate(340.0, threshold) is False
    assert passes_materiality_gate(0.0, threshold) is False


def test_passes_materiality_gate_negative_amounts():
    """Materiality gate tests absolute value abs(F_i)."""
    threshold = 500.0
    assert passes_materiality_gate(-600.0, threshold) is True
    assert passes_materiality_gate(-500.0, threshold) is True
    assert passes_materiality_gate(-340.0, threshold) is False


# ---------------------------------------------------------------------------
# Termination Check Tests (§3.6 Termination branches)
# ---------------------------------------------------------------------------

def test_check_termination_branch_fully_explained():
    """Branch 1: if abs(rho_k) < materiality_threshold -> FULLY_EXPLAINED, terminate."""
    threshold = 500.0

    # Residual well below threshold
    res = check_termination(
        residual=400.0,
        materiality_threshold=threshold,
        hypotheses_exhausted=False,
        step_count=1,
    )
    assert _matches_status(res, TerminationStatus.FULLY_EXPLAINED, "FULLY_EXPLAINED")

    # Residual negative but within threshold
    res_neg = check_termination(
        residual=-250.0,
        materiality_threshold=threshold,
        hypotheses_exhausted=False,
        step_count=2,
    )
    assert _matches_status(res_neg, TerminationStatus.FULLY_EXPLAINED, "FULLY_EXPLAINED")

    # Zero residual is fully explained even if hypotheses are exhausted or steps high
    res_zero = check_termination(
        residual=0.0,
        materiality_threshold=threshold,
        hypotheses_exhausted=True,
        step_count=10,
    )
    assert _matches_status(res_zero, TerminationStatus.FULLY_EXPLAINED, "FULLY_EXPLAINED")


def test_check_termination_branch_escalate_hypotheses_exhausted():
    """Branch 2A: residual >= threshold and hypotheses_exhausted is True -> ESCALATE."""
    threshold = 500.0

    res = check_termination(
        residual=5000.0,
        materiality_threshold=threshold,
        hypotheses_exhausted=True,
        step_count=3,
        max_steps=12,
    )
    assert _matches_status(res, TerminationStatus.ESCALATE, "ESCALATE")

    # Exactly at threshold with exhausted hypotheses
    res_edge = check_termination(
        residual=500.0,
        materiality_threshold=threshold,
        hypotheses_exhausted=True,
        step_count=1,
        max_steps=12,
    )
    assert _matches_status(res_edge, TerminationStatus.ESCALATE, "ESCALATE")


def test_check_termination_branch_escalate_loop_guard():
    """Branch 2B: residual >= threshold and step_count > max_steps -> ESCALATE."""
    threshold = 500.0

    # step_count 13 exceeds default max_steps=12
    res_default = check_termination(
        residual=5000.0,
        materiality_threshold=threshold,
        hypotheses_exhausted=False,
        step_count=13,
    )
    assert _matches_status(res_default, TerminationStatus.ESCALATE, "ESCALATE")

    # Explicit custom max_steps
    res_custom = check_termination(
        residual=5000.0,
        materiality_threshold=threshold,
        hypotheses_exhausted=False,
        step_count=7,
        max_steps=6,
    )
    assert _matches_status(res_custom, TerminationStatus.ESCALATE, "ESCALATE")


def test_check_termination_branch_continue():
    """Branch 3: residual >= threshold, hypotheses remaining, within step cap -> CONTINUE."""
    threshold = 500.0

    # Initial state: delta_0 = 44,000
    res_init = check_termination(
        residual=44000.0,
        materiality_threshold=threshold,
        hypotheses_exhausted=False,
        step_count=0,
    )
    assert _matches_status(res_init, TerminationStatus.CONTINUE, "CONTINUE")

    # Intermediate state: rho = 13,000, step 1
    res_step1 = check_termination(
        residual=13000.0,
        materiality_threshold=threshold,
        hypotheses_exhausted=False,
        step_count=1,
    )
    assert _matches_status(res_step1, TerminationStatus.CONTINUE, "CONTINUE")

    # Final Act II state: rho = 5,000, hypotheses remaining, step 2
    res_step2 = check_termination(
        residual=5000.0,
        materiality_threshold=threshold,
        hypotheses_exhausted=False,
        step_count=2,
    )
    assert _matches_status(res_step2, TerminationStatus.CONTINUE, "CONTINUE")

    # Loop guard boundary: step_count == max_steps (12) must still CONTINUE
    res_bound = check_termination(
        residual=5000.0,
        materiality_threshold=threshold,
        hypotheses_exhausted=False,
        step_count=12,
        max_steps=12,
    )
    assert _matches_status(res_bound, TerminationStatus.CONTINUE, "CONTINUE")


# ---------------------------------------------------------------------------
# Factor Quantification & Alpha Tests (§3.4)
# ---------------------------------------------------------------------------

def test_alpha_by_classification_keys():
    """Assert ALPHA_BY_CLASSIFICATION contains all classifications defined in §3.4."""
    expected_classifications = {
        "TIMING_UNBILLED",
        "MISCLASSIFICATION",
        "APPROVED_EXCLUSION",
        "FX_REVALUATION",
        "GENUINE_TP_DEVIATION",
    }
    assert isinstance(ALPHA_BY_CLASSIFICATION, dict)
    assert expected_classifications.issubset(set(ALPHA_BY_CLASSIFICATION.keys()))


def test_quantify_factor_all_classifications():
    """Assert alpha scaling for each classification:
    - TIMING_UNBILLED, MISCLASSIFICATION, APPROVED_EXCLUSION scale by m_target
    - FX_REVALUATION, GENUINE_TP_DEVIATION have alpha = 1.0
    """
    amounts = {"T1": 1000.0, "T2": 2000.0}
    m_target = 0.10

    # Scaled by m_target
    for cls in ("TIMING_UNBILLED", "MISCLASSIFICATION", "APPROVED_EXCLUSION"):
        factor = quantify_factor(["T1"], amounts, cls, m_target)
        assert factor == pytest.approx(100.0)

    # Dollar-for-dollar (alpha = 1.0)
    for cls in ("FX_REVALUATION", "GENUINE_TP_DEVIATION"):
        factor = quantify_factor(["T1"], amounts, cls, m_target)
        assert factor == pytest.approx(1000.0)

    # Multi-transaction sum
    multi_factor = quantify_factor(["T1", "T2"], amounts, "TIMING_UNBILLED", m_target)
    assert multi_factor == pytest.approx(300.0)

    # Empty transaction set yields 0.0
    zero_factor = quantify_factor([], amounts, "TIMING_UNBILLED", m_target)
    assert zero_factor == pytest.approx(0.0)


def test_compute_residual():
    """Assert residual computation rho_k = delta_0 - sum(accepted_factors)."""
    delta_0 = 44000.0
    assert compute_residual(delta_0, []) == pytest.approx(44000.0)
    assert compute_residual(delta_0, [31000.0]) == pytest.approx(13000.0)
    assert compute_residual(delta_0, [31000.0, 8000.0]) == pytest.approx(5000.0)
    assert compute_residual(delta_0, [31000.0, 8000.0, 5000.0]) == pytest.approx(0.0)
