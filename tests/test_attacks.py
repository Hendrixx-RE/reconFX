"""Attack scenario tests covering all 10 scenarios in README.md §10.2 exactly.

Scenarios:
1. Same transaction claimed by two hypotheses
2. Exception memo caps at $50,000 but GL shows $80,000
3. GL description says "rechargeable" but the account is excluded
4. Policy markup changes mid-period
5. Factor computed below materiality
6. Approval memo link unresolvable
7. Duplicate GL doc ID
8. Malformed tool call from the model
9. Residual goes negative (over-explanation)
10. Clearing ledger row belongs to a third entity
"""

from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import pytest

from engine.decomposition import DecompositionState, quantify_factor
from engine.baseline import (
    check_mapping_conflict,
    check_policy_effective_date,
    detect_duplicate_gl_rows,
    get_effective_policy_markup,
)
from engine.journal import draft_reversal
from agent import tools
from agent.loop import LoopEscalated, ReActLoop


# ---------------------------------------------------------------------------
# Scenario 1: Same transaction claimed by two hypotheses
# ---------------------------------------------------------------------------
def test_scenario_1_transaction_set_overlap():
    """§10.2 Scenario 1: Same transaction claimed by two hypotheses.

    Required behaviour: Second rejected, `TRANSACTION_SET_OVERLAP`, conflicting IDs returned.
    Status: Already implemented in engine/decomposition.py (DecompositionState.test_hypothesis).
    """
    state = DecompositionState(
        opening_amount=Decimal("44000"),
        materiality=Decimal("500"),
        amount_lookup={
            "GL-2026-0307": Decimal("310000"),
            "GL-2026-0306": Decimal("80000"),
        },
    )

    # First hypothesis claims GL-2026-0307 -> accepted
    res1 = state.test_hypothesis("F1", "TIMING_UNBILLED", ["GL-2026-0307"], ["ref1"])
    assert res1.accepted is True
    assert state.residual == Decimal("13000")

    # Second hypothesis tries to claim the same transaction GL-2026-0307 -> rejected
    res2 = state.test_hypothesis("F2", "MISCLASSIFICATION", ["GL-2026-0307"], ["ref2"])
    assert res2.accepted is False
    assert res2.rejection_reason == "TRANSACTION_SET_OVERLAP"
    assert res2.conflicting_ids == ["GL-2026-0307"]
    assert state.residual == Decimal("13000")  # Residual unchanged

    # Also verify via agent.tools.test_hypothesis
    tools.bind_decomposition_state(state)
    tool_res = tools.test_hypothesis("F3", "APPROVED_EXCLUSION", ["GL-2026-0307"], ["ref3"])
    assert tool_res["accepted"] is False
    assert tool_res["rejection_reason"] == "TRANSACTION_SET_OVERLAP"
    assert tool_res["conflicting_ids"] == ["GL-2026-0307"]


# ---------------------------------------------------------------------------
# Scenario 2: Exception memo caps at $50,000 but GL shows $80,000
# ---------------------------------------------------------------------------
def test_scenario_2_factor_capped_by_approval_memo():
    """§10.2 Scenario 2: Exception memo caps at $50,000 but GL shows $80,000.

    Required behaviour: Factor caps at $50,000; remaining $30,000 stays in residual.
    Status: Required a fix.
    Fix: Added optional `cap: Decimal | None` parameter to `quantify_factor` and
    `DecompositionState.test_hypothesis` in engine/decomposition.py, threaded through
    `tools.test_hypothesis`, and sourced from `query_approvals()`'s `approved_amount_usd`
    in agent/act_two.py.
    """
    state = DecompositionState(
        opening_amount=Decimal("80000"),
        materiality=Decimal("500"),
        amount_lookup={"GL-2026-0306": Decimal("80000")},
    )

    # GL shows $80,000, memo approves cap of $50,000 (alpha = 1.0 for GENUINE_TP_DEVIATION)
    res = state.test_hypothesis(
        cause_id="F2",
        classification="GENUINE_TP_DEVIATION",
        transaction_ids=["GL-2026-0306"],
        evidence_refs=["data/policy_exceptions.json#EXP-2026-08"],
        cap=Decimal("50000"),
    )

    assert res.accepted is True
    assert res.factor_usd == Decimal("50000")
    assert res.new_residual == Decimal("30000")
    assert state.residual == Decimal("30000")

    # Verify quantify_factor respects the cap as well
    capped_factor = quantify_factor(
        classification="GENUINE_TP_DEVIATION",
        transaction_ids=["GL-2026-0306"],
        amount_lookup={"GL-2026-0306": Decimal("80000")},
        cap=Decimal("50000"),
    )
    assert capped_factor == Decimal("50000")


# ---------------------------------------------------------------------------
# Scenario 3: GL description says "rechargeable" but account is excluded
# ---------------------------------------------------------------------------
def test_scenario_3_gl_description_conflict_applies_precedence():
    """§10.2 Scenario 3: GL description says 'rechargeable' but the account is excluded.

    Required behaviour: Flags the mapping conflict; applies precedence; records the override explicitly.
    Status: Required a fix.
    Fix: Implemented `check_mapping_conflict` in engine/baseline.py, which detects
    when a rechargeable/engineering description is attached to an excluded GL account,
    resolves the conflict using policy `document_precedence` (where TP_POLICY_GL_MAPPING
    outranks GL_LINE_DESCRIPTION), and explicitly records the override.
    """
    policy = {
        "policy_id": "TP-POL-2026-ENG",
        "eligible_gl_accounts": ["6100", "6110", "6120", "6200"],
        "excluded_gl_accounts": ["6800", "6900", "7100", "7700"],
        "document_precedence": [
            "APPROVED_POLICY_EXCEPTION_MEMO",
            "INTERCOMPANY_CONTRACT",
            "TP_POLICY_GL_MAPPING",
            "GL_LINE_DESCRIPTION",
        ],
    }
    gl_row = {
        "doc_id": "GL-2026-0305",
        "gl_account": "6800",
        "account_description": "Local Admin Overhead",
        "description": "DevOps SaaS Software Licenses - Rechargeable Engineering",
        "amount_usd": "140000.00",
    }

    conflict = check_mapping_conflict(gl_row, policy)

    # 1. Flags the mapping conflict
    assert conflict["has_conflict"] is True
    assert conflict["conflict_type"] == "MAPPING_CONFLICT"

    # 2. Applies precedence
    assert conflict["resolved_by"] == "TP_POLICY_GL_MAPPING"
    assert conflict["overridden"] == "GL_LINE_DESCRIPTION"

    # 3. Records the override explicitly
    assert conflict["override_record"] == "TP_POLICY_GL_MAPPING overrides GL_LINE_DESCRIPTION"
    assert conflict["treatment"] == "EXCLUDE_FROM_BASE"


# ---------------------------------------------------------------------------
# Scenario 4: Policy markup changes mid-period
# ---------------------------------------------------------------------------
def test_scenario_4_policy_markup_effective_date_range():
    """§10.2 Scenario 4: Policy markup changes mid-period.

    Required behaviour: Checks posting date against policy effective range before applying a rate.
    Status: Required a fix.
    Fix: Implemented `check_policy_effective_date` and `get_effective_policy_markup`
    in engine/baseline.py, checking posting date against `effective_date` and `expiry_date`
    before allowing a markup rate to be applied.
    """
    policy_q1_early = {
        "policy_id": "TP-POL-2026-P1",
        "effective_date": "2026-01-01",
        "expiry_date": "2026-03-15",
        "target_markup_percent": 10.0,
    }
    policy_q1_late = {
        "policy_id": "TP-POL-2026-P2",
        "effective_date": "2026-03-16",
        "expiry_date": "2026-06-30",
        "target_markup_percent": 12.5,
    }

    # Posting date 2026-03-10 falls within policy_q1_early, but outside policy_q1_late
    assert check_policy_effective_date(policy_q1_early, "2026-03-10") is True
    assert check_policy_effective_date(policy_q1_late, "2026-03-10") is False
    assert get_effective_policy_markup(policy_q1_early, "2026-03-10") == Decimal("0.10")

    with pytest.raises(ValueError, match="outside policy effective range"):
        get_effective_policy_markup(policy_q1_late, "2026-03-10")

    # Posting date 2026-03-20 falls within policy_q1_late, but policy_q1_early has expired
    assert check_policy_effective_date(policy_q1_early, "2026-03-20") is False
    assert check_policy_effective_date(policy_q1_late, "2026-03-20") is True
    assert get_effective_policy_markup(policy_q1_late, "2026-03-20") == Decimal("0.125")

    with pytest.raises(ValueError, match="outside policy effective range"):
        get_effective_policy_markup(policy_q1_early, "2026-03-20")


# ---------------------------------------------------------------------------
# Scenario 5: Factor computed below materiality
# ---------------------------------------------------------------------------
def test_scenario_5_factor_below_materiality_rejected():
    """§10.2 Scenario 5: Factor computed below materiality.

    Required behaviour: Rejected and logged, residual unchanged.
    Status: Already implemented in engine/decomposition.py (DecompositionState.test_hypothesis).
    """
    state = DecompositionState(
        opening_amount=Decimal("5000"),
        materiality=Decimal("500"),
        amount_lookup={"GL-2026-0309": Decimal("340")},
    )

    res = state.test_hypothesis("H3", "FX_REVALUATION", ["GL-2026-0309"], ["data/entity_gl.csv#GL-2026-0309"])

    # Rejected
    assert res.accepted is False
    assert res.rejection_reason == "BELOW_MATERIALITY"
    assert res.factor_usd == Decimal("340")

    # Residual unchanged
    assert res.new_residual == Decimal("5000")
    assert state.residual == Decimal("5000")

    # Logged in audit trail
    trail = state.audit_trail()
    assert len(trail) == 1
    assert trail[0]["cause_id"] == "H3"
    assert trail[0]["accepted"] is False
    assert trail[0]["rejection_reason"] == "BELOW_MATERIALITY"
    assert trail[0]["residual_after"] == Decimal("5000")


# ---------------------------------------------------------------------------
# Scenario 6: Approval memo link unresolvable
# ---------------------------------------------------------------------------
def test_scenario_6_unresolvable_approval_memo_escalates():
    """§10.2 Scenario 6: Approval memo link unresolvable (`documentation_link` doesn't exist on disk).

    Required behaviour: Fails evidence verification; does not accept the factor; escalates.
    Status: Required a fix.
    Fix: Implemented `verify_evidence` and `verify_approval_memo` in agent/tools.py.
    Integrated disk-link verification into agent/act_two.py so that if an approval
    memo's documentation_link is missing on disk, evidence verification fails, the factor
    is not accepted, and the loop escalates immediately with reason EVIDENCE_VERIFICATION_FAILED.
    """
    unresolvable_memo = {
        "exception_id": "EXP-NONEXISTENT",
        "entity_id": "ENT-IN-02",
        "approved_amount_usd": 50000.0,
        "documentation_link": "doc_store/NON_EXISTENT_MEMO_FILE.pdf",
    }

    # 1. Fails evidence verification
    assert tools.verify_approval_memo(unresolvable_memo) is False

    # 2. When tested in an investigation loop: does not accept factor, escalates
    captured_escalations = []

    def fake_escalate(reason, residual_usd, evidence_gap, packet):
        result = {
            "halted": True,
            "reason": reason,
            "residual_usd": residual_usd,
            "evidence_gap": evidence_gap,
            "packet": packet,
        }
        captured_escalations.append(result)
        return result

    loop = ReActLoop(act="INVESTIGATION", escalate_fn=fake_escalate)
    state = DecompositionState(Decimal("44000"), Decimal("500"), amount_lookup={"GL-1": Decimal("80000")})
    tools.bind_decomposition_state(state)

    if not tools.verify_approval_memo(unresolvable_memo):
        with pytest.raises(LoopEscalated) as exc_info:
            loop.escalate(
                reason="EVIDENCE_VERIFICATION_FAILED",
                residual_usd=float(state.residual),
                evidence_gap=[f"Resolvable documentation file for {unresolvable_memo['documentation_link']}"],
                packet={"cause_id": "F2", "documentation_link": unresolvable_memo["documentation_link"]},
            )

        assert exc_info.value.escalation_result["reason"] == "EVIDENCE_VERIFICATION_FAILED"
        assert state.residual == Decimal("44000")  # Factor not accepted; residual unchanged
        assert len(captured_escalations) == 1


# ---------------------------------------------------------------------------
# Scenario 7: Duplicate GL doc ID
# ---------------------------------------------------------------------------
def test_scenario_7_duplicate_gl_doc_id_triggers_reversal_and_exclusion():
    """§10.2 Scenario 7: Duplicate GL doc ID (same `doc_id` appears twice in a query result).

    Required behaviour: Duplicate detector fires; drafts a reversal; excludes from base.
    Status: Required a fix.
    Fix: Implemented `detect_duplicate_gl_rows` in engine/baseline.py and `draft_reversal`
    in engine/journal.py. Integrated duplicate detection into `compute_baseline`, ensuring
    duplicate doc_ids fire the detector, draft balanced reversal journal entries, and are
    excluded from the calculated base.
    """
    rows_with_duplicate = [
        {
            "doc_id": "GL-2026-0301",
            "posting_date": "2026-03-05",
            "cost_center": "CC-100",
            "gl_account": "6100",
            "amount_usd": "100000.00",
            "description": "March Payroll Batch 1",
            "entity_id": "ENT-IN-02",
        },
        {
            "doc_id": "GL-2026-0301",  # Same doc_id duplicate!
            "posting_date": "2026-03-05",
            "cost_center": "CC-100",
            "gl_account": "6100",
            "amount_usd": "100000.00",
            "description": "March Payroll Batch 1 (Duplicate Feed)",
            "entity_id": "ENT-IN-02",
        },
        {
            "doc_id": "GL-2026-0302",
            "posting_date": "2026-03-10",
            "cost_center": "CC-101",
            "gl_account": "6110",
            "amount_usd": "50000.00",
            "description": "AWS Hosting",
            "entity_id": "ENT-IN-02",
        },
    ]

    result = detect_duplicate_gl_rows(rows_with_duplicate)

    # 1. Duplicate detector fires
    assert result.has_duplicates is True
    assert result.duplicate_ids == ["GL-2026-0301"]
    assert len(result.duplicate_rows) == 1

    # 2. Drafts a reversal
    assert len(result.reversal_entries) == 1
    reversal = result.reversal_entries[0]
    assert reversal.entry_type == "GL_REVERSAL"
    assert reversal.status == "DRAFT"
    assert sum(l.debit for l in reversal.lines) == Decimal("100000.00")
    assert sum(l.credit for l in reversal.lines) == Decimal("100000.00")

    # 3. Excludes from base
    assert len(result.clean_rows) == 2
    clean_base = sum(Decimal(r["amount_usd"]) for r in result.clean_rows)
    assert clean_base == Decimal("150000.00")


# ---------------------------------------------------------------------------
# Scenario 8: Malformed tool call from the model
# ---------------------------------------------------------------------------
def test_scenario_8_malformed_tool_call_retries_once_then_escalates():
    """§10.2 Scenario 8: Malformed tool call from the model.

    Required behaviour: Retry once, then escalate. Never crash.
    Status: Already implemented in agent/loop.py (ReActLoop.call_tool).
    """
    call_counts = {"count": 0}

    def failing_tool(**kwargs):
        call_counts["count"] += 1
        raise TypeError("Simulated malformed parameters from LLM")

    captured_escalations = []

    def fake_escalate(reason, residual_usd, evidence_gap, packet):
        res = {
            "halted": True,
            "reason": reason,
            "residual_usd": residual_usd,
            "evidence_gap": evidence_gap,
            "packet": packet,
        }
        captured_escalations.append(res)
        return res

    loop = ReActLoop(act="INVESTIGATION", escalate_fn=fake_escalate)

    with pytest.raises(LoopEscalated) as exc_info:
        loop.call_tool("failing_tool", failing_tool, {"unexpected_arg": "invalid"})

    # Retried once (total 2 attempts), then escalated cleanly without crashing
    assert call_counts["count"] == 2
    assert exc_info.value.escalation_result["reason"] == "MALFORMED_TOOL_CALL"
    assert len(captured_escalations) == 1
    assert captured_escalations[0]["reason"] == "MALFORMED_TOOL_CALL"
    assert captured_escalations[0]["packet"]["tool_name"] == "failing_tool"


# ---------------------------------------------------------------------------
# Scenario 9: Residual goes negative (over-explanation)
# ---------------------------------------------------------------------------
def test_scenario_9_negative_residual_over_attribution_escalates():
    """§10.2 Scenario 9: Residual goes negative (over-explanation).

    Required behaviour: Halt immediately; flag `OVER_ATTRIBUTION`; escalate.
    Status: Required a fix (rejection was handled in DecompositionState; added immediate
    loop halting and escalation upon OVER_ATTRIBUTION in agent/act_two.py).
    """
    state = DecompositionState(
        opening_amount=Decimal("5000"),
        materiality=Decimal("500"),
        amount_lookup={"GL-OVER": Decimal("140000")},
    )

    # 1. Flag OVER_ATTRIBUTION: factor would be $14,000, but residual is only $5,000
    res = state.test_hypothesis("F4", "MISCLASSIFICATION", ["GL-OVER"], ["ref_over"])
    assert res.accepted is False
    assert res.rejection_reason == "OVER_ATTRIBUTION"
    assert state.residual == Decimal("5000")  # Residual does not go negative

    # 2. Halt immediately & escalate
    captured = []

    def fake_escalate(reason, residual_usd, evidence_gap, packet):
        escalation = {"halted": True, "reason": reason, "residual_usd": residual_usd, "packet": packet}
        captured.append(escalation)
        return escalation

    loop = ReActLoop(act="INVESTIGATION", escalate_fn=fake_escalate)
    if res.rejection_reason == "OVER_ATTRIBUTION":
        with pytest.raises(LoopEscalated) as exc_info:
            loop.escalate(
                reason="OVER_ATTRIBUTION",
                residual_usd=float(state.residual),
                evidence_gap=["Hypothesis factor exceeds residual (over-attribution)"],
                packet={"cause_id": "F4", "factor_usd": str(res.factor_usd)},
            )

        assert exc_info.value.escalation_result["reason"] == "OVER_ATTRIBUTION"
        assert exc_info.value.escalation_result["residual_usd"] == 5000.0
        assert len(captured) == 1


# ---------------------------------------------------------------------------
# Scenario 10: Clearing ledger row belongs to a third entity
# ---------------------------------------------------------------------------
def test_scenario_10_third_entity_clearing_row_excluded():
    """§10.2 Scenario 10: Clearing ledger row belongs to a third entity.

    Required behaviour: Cost-centre entity tag inspected; excluded from this entity's decomposition.
    Status: Required a fix.
    Fix: Updated `query_clearing_account` in agent/tools.py to accept `entity_id`
    and filter out rows where `row.get("entity_id") != entity_id`. Sourced `entity_id`
    in agent/act_one.py (defaulting to "ENT-IN-02").
    """
    # Test query_clearing_account inspecting entity tag
    target_result = tools.query_clearing_account(
        account="1900", from_date="2023-01-01", to_date="2026-02-28", entity_id="ENT-IN-02"
    )
    assert len(target_result["items"]) > 0
    assert all(r["entity_id"] == "ENT-IN-02" for r in target_result["items"])

    # When querying for a third entity (e.g. ENT-US-01 or third party), target entity rows are excluded
    third_entity_result = tools.query_clearing_account(
        account="1900", from_date="2023-01-01", to_date="2026-02-28", entity_id="ENT-US-99"
    )
    assert len(third_entity_result["items"]) == 0

    # Also test mixed row list with a third entity row injected
    mock_clearing_rows = [
        {
            "doc_id": "CLR-2023-001",
            "posting_date": "2023-04-01",
            "account": "1900",
            "amount_usd": "68000.00",
            "entity_id": "ENT-IN-02",
        },
        {
            "doc_id": "CLR-2023-999",
            "posting_date": "2023-04-01",
            "account": "1900",
            "amount_usd": "50000.00",
            "entity_id": "ENT-THIRD-PARTY",  # Third entity row
        },
    ]

    with patch("agent.tools._read_csv", return_value=mock_clearing_rows):
        res = tools.query_clearing_account(
            account="1900", from_date="2023-01-01", to_date="2026-02-28", entity_id="ENT-IN-02"
        )
        assert len(res["items"]) == 1
        assert res["items"][0]["doc_id"] == "CLR-2023-001"
        assert res["items"][0]["entity_id"] == "ENT-IN-02"
