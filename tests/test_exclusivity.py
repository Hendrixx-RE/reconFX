"""PLAN.md Phase 2 acceptance tests (§3.3 exclusivity, §3.5 materiality,
§3.6 termination, §5.3 journal balance)."""

from decimal import Decimal

import pytest

from engine.decomposition import DecompositionState, quantify_factor
from engine.journal import JournalEntry, JournalLine, draft_reclass


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
    """§10.2 attack #9: residual must never go negative."""
    s = DecompositionState(
        Decimal("5000"), Decimal("500"), amount_lookup={"GL-X": Decimal("140000")}
    )
    r = s.test_hypothesis("F4", "MISCLASSIFICATION", ["GL-X"], [])
    assert r.accepted is False
    assert r.rejection_reason == "OVER_ATTRIBUTION"
    assert s.residual == Decimal("5000")


def test_quantify_factor_does_not_touch_residual():
    """§2.4 H4: a recovery finding on a separate axis must not decrement
    the tracked residual, even though it uses the same alpha table."""
    s = DecompositionState(Decimal("5000"), Decimal("500"))
    recovery = quantify_factor(
        "MISCLASSIFICATION", ["GL-2026-0305"], {"GL-2026-0305": Decimal("140000")}
    )
    assert recovery == Decimal("14000")
    assert s.residual == Decimal("5000")


def test_journal_entries_balance():
    je = draft_reclass(Decimal("140000"), "6100", "6800")
    assert sum(l.debit for l in je.lines) == sum(l.credit for l in je.lines)


def test_unbalanced_journal_entry_rejected():
    with pytest.raises(ValueError):
        JournalEntry(
            entry_type="GL_RECLASS",
            lines=[
                JournalLine(account="6100", description="x", debit=Decimal("100")),
                JournalLine(account="6800", description="x", credit=Decimal("99")),
            ],
        )
