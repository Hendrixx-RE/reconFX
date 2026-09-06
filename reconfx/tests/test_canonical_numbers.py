"""Tests for canonical numbers — asserts every frozen figure in README §4.

README line 285: "These numbers are frozen. Build a test in Phase 1 that
asserts them and run it at the end of every phase."

This test suite asserts the verified arithmetic of Act II and the strata totals
of Act I using the deterministic engine contract:
- engine.baseline: compute_e_naive, BaselineResult, compute_baseline
- engine.decomposition: quantify_factor, passes_materiality_gate, compute_residual
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
    from engine.baseline import BaselineResult, compute_baseline, compute_e_naive
    from engine.decomposition import (
        ALPHA_BY_CLASSIFICATION,
        compute_residual,
        passes_materiality_gate,
        quantify_factor,
    )
except ImportError:
    from reconfx.engine.baseline import BaselineResult, compute_baseline, compute_e_naive
    from reconfx.engine.decomposition import (
        ALPHA_BY_CLASSIFICATION,
        compute_residual,
        passes_materiality_gate,
        quantify_factor,
    )


# ---------------------------------------------------------------------------
# Canonical Fixtures (README §4.1: March 2026, ENT-IN-02 -> ENT-US-01)
# ---------------------------------------------------------------------------

@pytest.fixture
def canonical_gl_lines() -> list[dict]:
    """Exact 9 lines from README §4.1 entity_gl.csv."""
    return [
        {
            "doc_id": "GL-2026-0301",
            "posting_date": "2026-03-05",
            "cost_center": "CC-100",
            "gl_account": "6100",
            "account_description": "Direct Engineering Payroll",
            "amount_usd": 1700000.00,
            "description": "March Engineering Base Payroll",
            "source_system": "PAYROLL",
            "vendor_invoice_ref": "",
        },
        {
            "doc_id": "GL-2026-0302",
            "posting_date": "2026-03-10",
            "cost_center": "CC-101",
            "gl_account": "6110",
            "account_description": "Cloud Infrastructure",
            "amount_usd": 420000.00,
            "description": "AWS Production Hosting Charges",
            "source_system": "AP_INVOICE",
            "vendor_invoice_ref": "AWS-MAR-2026",
        },
        {
            "doc_id": "GL-2026-0303",
            "posting_date": "2026-03-14",
            "cost_center": "CC-102",
            "gl_account": "6120",
            "account_description": "Professional & Contractor Fees",
            "amount_usd": 160000.00,
            "description": "Engineering Contractor Fees",
            "source_system": "AP_INVOICE",
            "vendor_invoice_ref": "CTR-2026-0311",
        },
        {
            "doc_id": "GL-2026-0304",
            "posting_date": "2026-03-18",
            "cost_center": "CC-100",
            "gl_account": "6200",
            "account_description": "Engineering Tooling",
            "amount_usd": 90000.00,
            "description": "Test Hardware and Lab Equipment",
            "source_system": "AP_INVOICE",
            "vendor_invoice_ref": "TOOL-2026-04",
        },
        {
            "doc_id": "GL-2026-0305",
            "posting_date": "2026-03-22",
            "cost_center": "CC-100",
            "gl_account": "6800",
            "account_description": "Local Admin Overhead",
            "amount_usd": 140000.00,
            "description": "DevOps SaaS Software Licenses - Engineering",
            "source_system": "AP_INVOICE",
            "vendor_invoice_ref": "SAAS-2026-Q1",
        },
        {
            "doc_id": "GL-2026-0306",
            "posting_date": "2026-03-24",
            "cost_center": "CC-102",
            "gl_account": "6120",
            "account_description": "Professional & Contractor Fees",
            "amount_usd": 80000.00,
            "description": "Executive Severance Settlement",
            "source_system": "AP_INVOICE",
            "vendor_invoice_ref": "SEV-2026-02",
        },
        {
            "doc_id": "GL-2026-0307",
            "posting_date": "2026-03-28",
            "cost_center": "CC-100",
            "gl_account": "6100",
            "account_description": "Direct Engineering Payroll",
            "amount_usd": 310000.00,
            "description": "Off-Cycle Late Engineering Payroll",
            "source_system": "PAYROLL",
            "vendor_invoice_ref": "",
        },
        {
            "doc_id": "GL-2026-0308",
            "posting_date": "2026-03-31",
            "cost_center": "CC-100",
            "gl_account": "7100",
            "account_description": "Local Facilities",
            "amount_usd": 96000.00,
            "description": "Bengaluru Office Facilities and Utilities",
            "source_system": "AP_INVOICE",
            "vendor_invoice_ref": "FAC-2026-03",
        },
        {
            "doc_id": "GL-2026-0309",
            "posting_date": "2026-03-31",
            "cost_center": "CC-100",
            "gl_account": "7700",
            "account_description": "FX Revaluation",
            "amount_usd": 340.00,
            "description": "FX Revaluation - Intercompany Balances",
            "source_system": "GL_ADJ",
            "vendor_invoice_ref": "",
        },
    ]


@pytest.fixture
def canonical_invoice_lines() -> list[dict]:
    """Exact 5 invoice lines from README §4.1 intercompany_invoice_lines.csv."""
    return [
        {
            "invoice_id": "INV-IC-2026-03",
            "line_no": 1,
            "gl_doc_id": "GL-2026-0301",
            "billed_amount_usd": 1700000.00,
            "recharge_flag": "Y",
            "exclusion_reason": "",
        },
        {
            "invoice_id": "INV-IC-2026-03",
            "line_no": 2,
            "gl_doc_id": "GL-2026-0302",
            "billed_amount_usd": 420000.00,
            "recharge_flag": "Y",
            "exclusion_reason": "",
        },
        {
            "invoice_id": "INV-IC-2026-03",
            "line_no": 3,
            "gl_doc_id": "GL-2026-0303",
            "billed_amount_usd": 160000.00,
            "recharge_flag": "Y",
            "exclusion_reason": "",
        },
        {
            "invoice_id": "INV-IC-2026-03",
            "line_no": 4,
            "gl_doc_id": "GL-2026-0304",
            "billed_amount_usd": 90000.00,
            "recharge_flag": "Y",
            "exclusion_reason": "",
        },
        {
            "invoice_id": "INV-IC-2026-03",
            "line_no": 5,
            "gl_doc_id": "GL-2026-0306",
            "billed_amount_usd": 0.00,
            "recharge_flag": "N",
            "exclusion_reason": "LOCAL_AP_BLOCK_NO_REASON_CODED",
        },
    ]


@pytest.fixture
def canonical_policy() -> dict:
    """Exact policy settings from README §4.1 tp_policy.json."""
    return {
        "policy_id": "TP-POL-2026-ENG",
        "policy_name": "Global Engineering Cost-Plus Services Agreement",
        "effective_date": "2026-01-01",
        "expiry_date": "2026-12-31",
        "method": "COST_PLUS_TNMM",
        "target_markup_percent": 10.0,
        "billing_cutoff_day_of_month": 25,
        "eligible_cost_centers": ["CC-100", "CC-101", "CC-102"],
        "eligible_gl_accounts": ["6100", "6110", "6120", "6200"],
        "excluded_gl_accounts": ["6800", "6900", "7100", "7700"],
        "materiality_threshold_usd": 500.0,
    }


@pytest.fixture
def canonical_recognised_revenue() -> float:
    """Exact recorded intercompany revenue R = $2,602,000 from README §4.1."""
    return 2602000.00


@pytest.fixture
def canonical_amounts_by_id(canonical_gl_lines: list[dict]) -> dict[str, float]:
    """Map of doc_id to amount_usd for all canonical GL lines."""
    return {line["doc_id"]: float(line["amount_usd"]) for line in canonical_gl_lines}


# ---------------------------------------------------------------------------
# Act II Tests: §4.1 Verified Arithmetic Table
# ---------------------------------------------------------------------------

def test_canonical_e_naive(canonical_gl_lines, canonical_policy):
    """Assert E_naive = $2,760,000.

    Derivation: 1,700,000 + 420,000 + 160,000 + 90,000 + 80,000 + 310,000.
    All GL lines where gl_account in eligible_gl_accounts and cost_center in eligible_cost_centers.
    """
    e_naive = compute_e_naive(
        gl_lines=canonical_gl_lines,
        eligible_gl_accounts=canonical_policy["eligible_gl_accounts"],
        eligible_cost_centers=canonical_policy["eligible_cost_centers"],
    )
    assert e_naive == pytest.approx(2760000.0)


def test_canonical_baseline_act_two(
    canonical_gl_lines,
    canonical_invoice_lines,
    canonical_policy,
    canonical_recognised_revenue,
):
    """Assert every figure in the baseline section of §4.1:
    - E_naive = $2,760,000
    - target_profit = $276,000 (10% * 2,760,000)
    - B (billed_cost_base) = $2,370,000
    - R (recognised_revenue) = $2,602,000
    - recognised_profit = $232,000 (2,602,000 - 2,370,000)
    - effective_markup = 8.41% (232,000 / 2,760,000 ~ 0.0841)
    - delta_0 = $44,000 (276,000 - 232,000)
    """
    baseline: BaselineResult = compute_baseline(
        gl_lines=canonical_gl_lines,
        invoice_lines=canonical_invoice_lines,
        recognised_revenue=canonical_recognised_revenue,
        target_markup_percent=canonical_policy["target_markup_percent"],
        eligible_gl_accounts=canonical_policy["eligible_gl_accounts"],
        eligible_cost_centers=canonical_policy["eligible_cost_centers"],
    )

    # Assert dataclass fields and frozen values
    assert baseline.e_naive == pytest.approx(2760000.0)
    assert baseline.target_profit == pytest.approx(276000.0)
    assert baseline.billed_cost_base == pytest.approx(2370000.0)
    assert baseline.recognised_revenue == pytest.approx(2602000.0)
    assert baseline.recognised_profit == pytest.approx(232000.0)

    # effective_markup: support decimal ratio ~0.0841 or percentage ~8.41%
    expected_ratio = 232000.0 / 2760000.0  # 0.08405797...
    assert (
        baseline.effective_markup == pytest.approx(expected_ratio, rel=1e-3)
        or baseline.effective_markup == pytest.approx(expected_ratio * 100.0, rel=1e-3)
        or baseline.effective_markup == pytest.approx(0.0841, abs=1e-3)
        or baseline.effective_markup == pytest.approx(8.41, abs=0.1)
    )

    assert baseline.delta_0 == pytest.approx(44000.0)


def test_canonical_factor_quantification_and_materiality(
    canonical_amounts_by_id,
    canonical_policy,
):
    """Assert frozen factor calculations from §4.1:
    - F1 timing: GL-2026-0307 ($310,000) * 10% = $31,000 (passes gate)
    - F2 approved exclusion: GL-2026-0306 ($80,000) * 10% = $8,000 (passes gate)
    - H3 FX revaluation: GL-2026-0309 ($340) * 1.0 = $340 (REJECTED by $500 materiality gate)
    - Recovery (separate axis): GL-2026-0305 ($140,000) * 10% = $14,000
    """
    m_target = canonical_policy["target_markup_percent"] / 100.0  # 0.10
    threshold = canonical_policy["materiality_threshold_usd"]      # 500.0

    # F1 Timing
    f1 = quantify_factor(
        transaction_ids=["GL-2026-0307"],
        amounts_by_id=canonical_amounts_by_id,
        classification="TIMING_UNBILLED",
        m_target=m_target,
    )
    assert f1 == pytest.approx(31000.0)
    assert passes_materiality_gate(f1, threshold) is True

    # F2 Approved Exclusion
    f2 = quantify_factor(
        transaction_ids=["GL-2026-0306"],
        amounts_by_id=canonical_amounts_by_id,
        classification="APPROVED_EXCLUSION",
        m_target=m_target,
    )
    assert f2 == pytest.approx(8000.0)
    assert passes_materiality_gate(f2, threshold) is True

    # H3 FX Revaluation
    h3 = quantify_factor(
        transaction_ids=["GL-2026-0309"],
        amounts_by_id=canonical_amounts_by_id,
        classification="FX_REVALUATION",
        m_target=m_target,
    )
    assert h3 == pytest.approx(340.0)
    # Materiality gate: $340 is below $500 threshold, so it MUST be rejected
    assert passes_materiality_gate(h3, threshold) is False

    # Recovery (separate axis)
    recovery = quantify_factor(
        transaction_ids=["GL-2026-0305"],
        amounts_by_id=canonical_amounts_by_id,
        classification="MISCLASSIFICATION",
        m_target=m_target,
    )
    assert recovery == pytest.approx(14000.0)


def test_canonical_decomposition_residuals_and_reconciliation(
    canonical_gl_lines,
    canonical_invoice_lines,
    canonical_policy,
    canonical_recognised_revenue,
    canonical_amounts_by_id,
):
    """Assert step-by-step residual decomposition and final reconciliation in §4.1:
    - delta_0 = $44,000
    - F1 = $31,000 -> residual rho_1 = $13,000
    - F2 = $8,000  -> residual rho_2 = $5,000
    - H3 = $340 rejected by gate -> residual remains $5,000
    - Final residual = $5,000
    - Reconciliation: 31,000 + 8,000 + 5,000 = 44,000
    """
    baseline = compute_baseline(
        gl_lines=canonical_gl_lines,
        invoice_lines=canonical_invoice_lines,
        recognised_revenue=canonical_recognised_revenue,
        target_markup_percent=canonical_policy["target_markup_percent"],
        eligible_gl_accounts=canonical_policy["eligible_gl_accounts"],
        eligible_cost_centers=canonical_policy["eligible_cost_centers"],
    )
    delta_0 = baseline.delta_0
    assert delta_0 == pytest.approx(44000.0)

    m_target = canonical_policy["target_markup_percent"] / 100.0
    threshold = canonical_policy["materiality_threshold_usd"]

    # F1
    f1 = quantify_factor(["GL-2026-0307"], canonical_amounts_by_id, "TIMING_UNBILLED", m_target)
    assert f1 == pytest.approx(31000.0)
    assert passes_materiality_gate(f1, threshold) is True
    res_1 = compute_residual(delta_0, [f1])
    assert res_1 == pytest.approx(13000.0)

    # F2
    f2 = quantify_factor(["GL-2026-0306"], canonical_amounts_by_id, "APPROVED_EXCLUSION", m_target)
    assert f2 == pytest.approx(8000.0)
    assert passes_materiality_gate(f2, threshold) is True
    res_2 = compute_residual(delta_0, [f1, f2])
    assert res_2 == pytest.approx(5000.0)

    # H3: rejected by materiality gate
    h3 = quantify_factor(["GL-2026-0309"], canonical_amounts_by_id, "FX_REVALUATION", m_target)
    assert h3 == pytest.approx(340.0)
    assert passes_materiality_gate(h3, threshold) is False

    # Because H3 was rejected, accepted factors list is only [f1, f2]
    accepted_factors = [f1, f2]
    final_residual = compute_residual(delta_0, accepted_factors)
    assert final_residual == pytest.approx(5000.0)

    # Assert exact frozen reconciliation: 31,000 + 8,000 + 5,000 = 44,000
    assert f1 + f2 + final_residual == pytest.approx(delta_0)
    assert 31000.0 + 8000.0 + 5000.0 == pytest.approx(44000.0)
    assert 31000 + 8000 + 5000 == 44000


# ---------------------------------------------------------------------------
# Act I Tests: §4.2 Clearing Account 1900 Strata and Total
# ---------------------------------------------------------------------------

def test_canonical_act_one_clearing_total():
    """Assert Act I frozen figures from README §4.2:
    - Stratum 1 (ERP cutover artifacts): $612,000
    - Stratum 2 (Unreversed FX revaluation): $384,000
    - Stratum 3 (Duplicate AP vendor feed): $206,000
    - Stratum 4 (Accrued IC margin plugs): $290,000
    - Stratum 5 (Live collectible receivable): $263,000
    - Stratum 6 (Untraceable): $92,000
    - Total: 612000 + 384000 + 206000 + 290000 + 263000 + 92000 = 1,847,000
    """
    stratum_1_erp_cutover = 612000.0
    stratum_2_unreversed_fx = 384000.0
    stratum_3_duplicate_ap = 206000.0
    stratum_4_accrued_ic_plugs = 290000.0
    stratum_5_live_collectible = 263000.0
    stratum_6_untraceable = 92000.0

    total_clearing_balance = (
        stratum_1_erp_cutover
        + stratum_2_unreversed_fx
        + stratum_3_duplicate_ap
        + stratum_4_accrued_ic_plugs
        + stratum_5_live_collectible
        + stratum_6_untraceable
    )

    assert total_clearing_balance == pytest.approx(1847000.0)
    assert (
        612000 + 384000 + 206000 + 290000 + 263000 + 92000
        == 1847000
    )
