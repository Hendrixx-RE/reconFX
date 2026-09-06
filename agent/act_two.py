"""Act II — the live investigation (README.md §2.4, §5.3 agent/act_two.py).

compute_baseline() -> load cause_profile.json, order hypotheses by prior ->
emit event showing WHY this order -> test H1 timing -> test H2 approved
exclusion -> test H3 FX (rejected) -> test H4 misclassification (recovery,
separate axis) -> residual -> draft true-up JE -> escalate().

No live model is wired yet (agent/model.py is a stub — see Phase 4). Per
README.md Phase 3 cut list #1 ("fix the stratum/hypothesis order rather than
having the LLM propose it; keep confirmation"), the hypothesis order here
is scripted from cause_profile.json's recommended_hypothesis_order, and
each hypothesis is still *confirmed* by real tool calls and gated by the
real DecompositionState — nothing about the financial result is hardcoded.
Swapping in a real LLM later only changes how the next hypothesis is
chosen, never how it is validated.
"""

import csv
import json
from decimal import Decimal
from pathlib import Path
from typing import Callable, Optional

from engine.baseline import compute_baseline, check_mapping_conflict
from engine.decomposition import DecompositionState, quantify_factor
from agent import tools
from agent.tools import span
from agent.loop import ReActLoop, LoopEscalated
from agent.prompts import ACT_TWO_TASK_PROMPT, hypothesis_prompt

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _load_cause_profile() -> dict:
    with open(DATA_DIR / "cause_profile.json", encoding="utf-8") as f:
        return json.load(f)


@span(kind="REASONING")
def generate_hypotheses(context: Optional[dict] = None, prior: Optional[dict] = None) -> list[str]:
    """Propose hypothesis order from cause profile prior (README §6.4)."""
    source = prior if prior is not None else (context or {})
    return source.get("recommended_hypothesis_order", [])


def _load_invoice_summary(period: str) -> Optional[dict]:
    """Direct reference-data read (not a dollar computation) for the
    escalation narrative — the applied markup vs. contractual target."""
    path = DATA_DIR / "intercompany_invoices.csv"
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["invoice_date"].startswith(period):
                return row
    return None


def run_act_two(
    entity_id: str = "ENT-IN-02",
    period: str = "2026-03",
    on_event: Optional[Callable[[dict], None]] = None,
) -> dict:
    """Runs the full Act II investigation. Returns a summary dict including
    the final residual, accepted factors, rejected hypotheses, the recovery
    finding, and the escalation packet (if any). Deterministic: repeated
    calls produce identical numbers."""

    baseline = compute_baseline(entity_id, period)
    policy_bundle = tools.get_policy(entity_id, period)
    policy = policy_bundle["policy"]
    materiality = Decimal(str(policy["materiality_threshold_usd"]))
    target_markup = Decimal(str(policy["target_markup_percent"])) / Decimal("100")

    cause_profile = _load_cause_profile()

    gl_rows = tools.query_gl(
        entity_id=entity_id, period_start=f"{period}-01", period_end=f"{period}-31"
    )["items"]
    amount_lookup = {row["doc_id"]: Decimal(row["amount_usd"]) for row in gl_rows}

    state = DecompositionState(
        opening_amount=baseline.deviation,
        materiality=materiality,
        target_markup=target_markup,
        amount_lookup=amount_lookup,
    )
    tools.bind_decomposition_state(state)

    loop = ReActLoop(act="INVESTIGATION", escalate_fn=tools.escalate, on_event=on_event)

    hypothesis_order = generate_hypotheses(
        context={"residual": state.residual},
        prior=cause_profile,
    )

    loop.record_hypothesis_event(
        "HYPOTHESIS",
        {
            "message": ACT_TWO_TASK_PROMPT,
            "baseline": {
                "eligible_base": str(baseline.eligible_base),
                "target_profit": str(baseline.target_profit),
                "billed_base": str(baseline.billed_base),
                "recognised_profit": str(baseline.recognised_profit),
                "effective_markup": str(baseline.effective_markup),
                "deviation": str(baseline.deviation),
            },
            "cause_profile_order": hypothesis_order,
            "reason": hypothesis_prompt({"residual": state.residual}, cause_profile),
        },
    )

    accepted_factors = []
    rejected_hypotheses = []
    recovery_findings = []

    try:
        # H1 — TIMING_UNBILLED: off-cycle payroll posted after billing cutoff.
        payroll = loop.call_tool(
            "query_payroll", tools.query_payroll, {"entity_id": entity_id, "period": period}
        )
        late_runs = [
            p for p in payroll["items"] if p["posting_date"] > f"{period}-{policy['billing_cutoff_day_of_month']:02d}"
        ]
        gl_check = loop.call_tool(
            "query_gl",
            tools.query_gl,
            {
                "entity_id": entity_id,
                "period_start": f"{period}-01",
                "period_end": f"{period}-31",
                "description_contains": "Off-Cycle",
            },
        )
        late_gl_ids = [row["doc_id"] for row in gl_check["items"]]
        h1_result = loop.call_tool(
            "test_hypothesis",
            tools.test_hypothesis,
            {
                "cause_id": "F1",
                "classification": "TIMING_UNBILLED",
                "transaction_ids": late_gl_ids,
                "evidence_refs": payroll["evidence_refs"] + gl_check["evidence_refs"],
            },
        )
        if h1_result["accepted"]:
            accepted_factors.append({"cause_id": "F1", "classification": "TIMING_UNBILLED", **h1_result})
            loop.record_hypothesis_event(
                "FACTOR_ACCEPTED",
                {"cause_id": "F1", "label": "Unbilled late payroll", "disposition": "ROLL_TO_APRIL_BILLING", **h1_result},
            )
        elif h1_result.get("rejection_reason") == "OVER_ATTRIBUTION":
            loop.escalate(
                reason="OVER_ATTRIBUTION",
                residual_usd=float(state.residual),
                evidence_gap=["Factor for F1 exceeds remaining residual (over-attribution)"],
                packet={"cause_id": "F1", **h1_result},
            )

        # H2 — APPROVED_EXCLUSION: severance excluded by memo, counted by the naive base.
        approvals = loop.call_tool(
            "query_approvals",
            tools.query_approvals,
            {"entity_id": entity_id, "period": period, "gl_account": "6120"},
        )
        severance_gl = loop.call_tool(
            "query_gl",
            tools.query_gl,
            {
                "entity_id": entity_id,
                "period_start": f"{period}-01",
                "period_end": f"{period}-31",
                "description_contains": "Severance",
            },
        )
        severance_ids = [row["doc_id"] for row in severance_gl["items"]]
        h2_result = None
        if approvals["items"] and severance_ids:
            memo = approvals["items"][0]
            # Verify approval memo link exists on disk (§10.2 attack #6)
            if not tools.verify_approval_memo(memo):
                loop.record_hypothesis_event(
                    "EVIDENCE_VERIFICATION_FAILED",
                    {"cause_id": "F2", "documentation_link": memo.get("documentation_link")},
                )
                loop.escalate(
                    reason="EVIDENCE_VERIFICATION_FAILED",
                    residual_usd=float(state.residual),
                    evidence_gap=[f"Resolvable documentation file for {memo.get('documentation_link')}"],
                    packet={"cause_id": "F2", "documentation_link": memo.get("documentation_link")},
                )

            approved_cap = (
                Decimal(str(memo["approved_amount_usd"]))
                if "approved_amount_usd" in memo and memo["approved_amount_usd"] is not None
                else None
            )
            h2_result = loop.call_tool(
                "test_hypothesis",
                tools.test_hypothesis,
                {
                    "cause_id": "F2",
                    "classification": "APPROVED_EXCLUSION",
                    "transaction_ids": severance_ids,
                    "evidence_refs": approvals["evidence_refs"] + severance_gl["evidence_refs"],
                    "cap": approved_cap,
                },
            )
            if h2_result["accepted"]:
                accepted_factors.append({"cause_id": "F2", "classification": "APPROVED_EXCLUSION", **h2_result})
                loop.record_hypothesis_event(
                    "FACTOR_ACCEPTED",
                    {
                        "cause_id": "F2",
                        "label": "Approved policy exclusion overrides GL mapping",
                        "disposition": "RESTATE_COMPLIANCE_BASE",
                        "precedence_note": "APPROVED_POLICY_EXCEPTION_MEMO overrides TP_POLICY_GL_MAPPING",
                        **h2_result,
                    },
                )
            elif h2_result.get("rejection_reason") == "OVER_ATTRIBUTION":
                loop.escalate(
                    reason="OVER_ATTRIBUTION",
                    residual_usd=float(state.residual),
                    evidence_gap=["Factor for F2 exceeds remaining residual (over-attribution)"],
                    packet={"cause_id": "F2", **h2_result},
                )

        # H3 — FX_REVALUATION: test, expect rejection below materiality.
        fx_gl = loop.call_tool(
            "query_gl",
            tools.query_gl,
            {
                "entity_id": entity_id,
                "period_start": f"{period}-01",
                "period_end": f"{period}-31",
                "gl_accounts": ["7700"],
            },
        )
        fx_ids = [row["doc_id"] for row in fx_gl["items"]]
        if fx_ids:
            h3_result = loop.call_tool(
                "test_hypothesis",
                tools.test_hypothesis,
                {
                    "cause_id": "H3",
                    "classification": "FX_REVALUATION",
                    "transaction_ids": fx_ids,
                    "evidence_refs": fx_gl["evidence_refs"],
                },
            )
            if not h3_result["accepted"]:
                if h3_result.get("rejection_reason") == "OVER_ATTRIBUTION":
                    loop.escalate(
                        reason="OVER_ATTRIBUTION",
                        residual_usd=float(state.residual),
                        evidence_gap=["Factor for H3 exceeds remaining residual (over-attribution)"],
                        packet={"cause_id": "H3", **h3_result},
                    )
                rejected_hypotheses.append(
                    {
                        "hypothesis": "FX_REVALUATION",
                        "computed_impact_usd": h3_result["factor_usd"],
                        "rejection_reason": h3_result["rejection_reason"],
                        "threshold_usd": str(materiality),
                    }
                )
                loop.record_hypothesis_event("FACTOR_REJECTED", {"cause_id": "H3", **h3_result})

        # H4 — MISCLASSIFICATION (separate axis): rechargeable cost stranded
        # in an excluded account. Never counted in E_naive, so it cannot
        # reduce the tracked residual — quantified independently.
        saas_gl = loop.call_tool(
            "query_gl",
            tools.query_gl,
            {
                "entity_id": entity_id,
                "period_start": f"{period}-01",
                "period_end": f"{period}-31",
                "gl_accounts": ["6800"],
                "description_contains": "SaaS",
            },
        )
        if saas_gl["items"]:
            for item in saas_gl["items"]:
                conflict = check_mapping_conflict(item, policy)
                if conflict.get("has_conflict"):
                    loop.record_hypothesis_event("MAPPING_CONFLICT", conflict)
            saas_ids = [row["doc_id"] for row in saas_gl["items"]]
            amount_lookup = {row["doc_id"]: Decimal(row["amount_usd"]) for row in saas_gl["items"]}
            recovery_amount = quantify_factor(
                classification="MISCLASSIFICATION",
                transaction_ids=saas_ids,
                amount_lookup=amount_lookup,
                target_markup=target_markup,
            )
            je = loop.call_tool(
                "draft_journal_entry",
                tools.draft_journal_entry,
                {
                    "entry_type": "GL_RECLASS",
                    "lines": [
                        {"account": "6100", "description": "Reclass rechargeable engineering software", "debit": float(sum(amount_lookup.values()))},
                        {"account": "6800", "description": "Reclass rechargeable engineering software", "credit": float(sum(amount_lookup.values()))},
                    ],
                    "supporting_evidence": saas_gl["evidence_refs"],
                    "requires_approval": True,
                },
            )
            recovery_findings.append(
                {
                    "label": "Misclassified rechargeable software",
                    "amount_usd": str(sum(amount_lookup.values())),
                    "entitlement_impact_usd": str(recovery_amount),
                    "proposed_entry": je,
                }
            )
            loop.record_hypothesis_event(
                "RECOVERY_FOUND",
                {"cause_id": "F4", "label": "Misclassified rechargeable software", "entitlement_impact_usd": str(recovery_amount)},
            )

        # Residual: escalate if not fully explained.
        if not state.is_fully_explained:
            invoice_row = _load_invoice_summary(period)
            je = loop.call_tool(
                "draft_journal_entry",
                tools.draft_journal_entry,
                {
                    "entry_type": "TP_TRUE_UP",
                    "lines": [
                        {"entity": entity_id, "account": "1200", "description": "Intercompany Receivable - US Parent", "debit": float(state.residual)},
                        {"entity": entity_id, "account": "4100", "description": "Intercompany Service Revenue", "credit": float(state.residual)},
                    ],
                    "supporting_evidence": ["data/intercompany_invoices.csv#INV-IC-2026-03"],
                    "requires_approval": True,
                },
            )
            packet = {
                "escalation_id": f"ESC-{period}-001",
                "entity_id": entity_id,
                "period": period,
                "opening_deviation_usd": str(baseline.deviation),
                "explained_usd": str(baseline.deviation - state.residual),
                "residual_usd": str(state.residual),
                "factors": accepted_factors,
                "rejected_hypotheses": rejected_hypotheses,
                "recovery_findings": recovery_findings,
                "probable_cause": (
                    f"Effective markup applied was {invoice_row['markup_applied_percent']}% "
                    f"against a contractual {policy['target_markup_percent']}% on billed base "
                    f"${invoice_row['billed_cost_base_usd']}"
                    if invoice_row
                    else "Effective markup applied deviated from contractual target; invoice detail unavailable"
                ),
                "confidence": "PROBABLE_UNPROVEN",
                "evidence_gap": [
                    f"{period} billing-run configuration export (markup rate parameter)",
                    f"Billing engine change log for period {period}",
                ],
                "proposed_journal_entry": je,
            }
            loop.escalate(
                reason="RESIDUAL_UNEXPLAINED",
                residual_usd=float(state.residual),
                evidence_gap=packet["evidence_gap"],
                packet=packet,
            )

    except LoopEscalated as exc:
        return {
            "entity_id": entity_id,
            "period": period,
            "baseline": baseline,
            "residual": state.residual,
            "accepted_factors": accepted_factors,
            "rejected_hypotheses": rejected_hypotheses,
            "recovery_findings": recovery_findings,
            "escalation": exc.escalation_result,
            "audit_trail": state.audit_trail(),
        }

    return {
        "entity_id": entity_id,
        "period": period,
        "baseline": baseline,
        "residual": state.residual,
        "accepted_factors": accepted_factors,
        "rejected_hypotheses": rejected_hypotheses,
        "recovery_findings": recovery_findings,
        "escalation": None,
        "audit_trail": state.audit_trail(),
    }


if __name__ == "__main__":
    from integrations.ao_client import handle_event

    def _on_event(e: dict) -> None:
        print(e)
        handle_event(e)

    result = run_act_two(on_event=_on_event)
    print("\n--- SUMMARY ---")
    print(f"Residual: {result['residual']}")
    print(f"Accepted factors: {len(result['accepted_factors'])}")
    print(f"Recovery findings: {len(result['recovery_findings'])}")
    print(f"Escalated: {result['escalation'] is not None}")
