"""Phase 3 acceptance tests (README.md Phase 3 acceptance criteria).

- Act II produces identical numbers across repeated runs.
- Act I and Act II reconcile to the canonical §4 figures.
- A malformed tool call retries once, then escalates instead of crashing.
- The loop halts at the step cap rather than looping indefinitely.
"""

from decimal import Decimal

import pytest

from agent.act_one import run_act_one
from agent.act_two import run_act_two
from agent.loop import LoopEscalated, ReActLoop


def test_act_two_reproducible_across_runs():
    results = [run_act_two() for _ in range(3)]
    for r in results:
        assert r["residual"] == Decimal("5000.000")
        assert len(r["accepted_factors"]) == 2
        assert r["accepted_factors"][0]["factor_usd"] == "31000.000"
        assert r["accepted_factors"][1]["factor_usd"] == "8000.000"
        assert len(r["rejected_hypotheses"]) == 1
        assert r["rejected_hypotheses"][0]["rejection_reason"] == "BELOW_MATERIALITY"
        assert len(r["recovery_findings"]) == 1
        assert r["recovery_findings"][0]["entitlement_impact_usd"] == "14000.000"
        assert r["escalation"] is not None


def test_act_two_factors_reconcile_to_44000():
    r = run_act_two()
    total_explained = sum(Decimal(f["factor_usd"]) for f in r["accepted_factors"])
    assert total_explained + r["residual"] == Decimal("44000.00")


def test_act_one_strata_reconcile_to_1847000():
    r = run_act_one()
    assert r["opening_balance"] == Decimal("1847000.00")
    assert r["residual"] == Decimal("0")
    assert len(r["strata"]) == 6


def test_act_one_escalates_untraceable_stratum():
    r = run_act_one()
    untraceable = [s for s in r["strata"] if s["classification"] == "UNTRACEABLE"]
    assert len(untraceable) == 1
    assert untraceable[0]["factor_usd"] == "92000.000"
    assert r["escalation"] is not None
    assert r["escalation"]["reason"] == "UNTRACEABLE_CLEARING_BALANCE"


def test_malformed_tool_call_retries_once_then_escalates():
    calls = {"count": 0}

    def flaky_tool(**kwargs):
        calls["count"] += 1
        raise TypeError("simulated malformed call")

    captured_escalations = []

    def fake_escalate(reason, residual_usd, evidence_gap, packet):
        result = {"halted": True, "reason": reason, "residual_usd": residual_usd, "evidence_gap": evidence_gap, "packet": packet}
        captured_escalations.append(result)
        return result

    loop = ReActLoop(act="INVESTIGATION", escalate_fn=fake_escalate)

    with pytest.raises(LoopEscalated):
        loop.call_tool("flaky_tool", flaky_tool, {"bad_kw": "x"})

    assert calls["count"] == 2  # original attempt + one retry
    assert captured_escalations[0]["reason"] == "MALFORMED_TOOL_CALL"


def test_loop_halts_at_step_cap():
    def noop_tool():
        return {"ok": True}

    def fake_escalate(reason, residual_usd, evidence_gap, packet):
        return {"halted": True, "reason": reason, "residual_usd": residual_usd, "evidence_gap": evidence_gap, "packet": packet}

    loop = ReActLoop(act="INVESTIGATION", escalate_fn=fake_escalate, max_steps=3)

    with pytest.raises(LoopEscalated) as exc_info:
        for _ in range(10):
            loop.call_tool("noop_tool", noop_tool, {})

    assert exc_info.value.escalation_result["reason"] == "MAX_STEPS_EXCEEDED"
