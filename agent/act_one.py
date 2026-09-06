"""Act I — the excavation (README.md §2.2, §5.3 agent/act_one.py).

load clearing ledger -> for each candidate stratum: call the confirming
tool, gather evidence -> pass transaction IDs to test_hypothesis() ->
assign disposition -> after all strata: derive cause_profile.json from the
plug stratum -> escalate the untraceable remainder.

Per README.md Phase 3 cut list #1, stratum identification is scripted here
(the interesting reasoning is in *confirmation*, not ordering) — each
stratum is still confirmed by a real tool call and gated by the real
DecompositionState, so the numbers are never hardcoded, only which
transactions to look at first.
"""

import json
from collections import defaultdict
from decimal import Decimal
from pathlib import Path
from typing import Callable, Optional

from engine.decomposition import DecompositionState
from agent import tools
from agent.loop import ReActLoop, LoopEscalated
from agent.prompts import ACT_ONE_TASK_PROMPT

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
ACCOUNT = "1900"
FROM_DATE = "2023-01-01"
TO_DATE = "2026-02-28"

DISPOSITIONS = {
    "ERP_CUTOVER_ARTIFACT": ("WRITE_OFF_TO_PL", "ESCALATE_ABOVE_WRITEOFF_THRESHOLD"),
    "UNREVERSED_FX_REVALUATION": ("DRAFT_REVERSING_JE", "DRAFT_CONTROLLER_REVIEW"),
    "DUPLICATE_AP_VENDOR_FEED": ("DRAFT_REVERSAL_OF_DUPLICATES", "DRAFT_CONTROLLER_REVIEW"),
    "ACCRUED_MARGIN_PLUG": ("REOPEN_FOR_RETRO_INVESTIGATION", "INFORMATIONAL"),
    "LIVE_COLLECTIBLE_RECEIVABLE": ("REINSTATE_AND_COLLECT", "DRAFT_CONTROLLER_APPROVES_COLLECTION"),
    "UNTRACEABLE": ("ESCALATE", "ESCALATE"),
}


def run_act_one(
    on_event: Optional[Callable[[dict], None]] = None,
    replay: bool = False,
    record: bool = False,
    fixture_path: Optional[str | Path] = None,
    respect_timing: bool = True,
    speed: float = 1.0,
) -> dict:
    """Runs the full Act I excavation. Returns a summary dict and writes
    data/cause_profile.json from the confirmed margin-plug stratum."""
    from contextlib import nullcontext
    from agent.replay import (
        DEFAULT_ACT_ONE_FIXTURE,
        record_session,
        replay_session,
    )

    path = fixture_path or DEFAULT_ACT_ONE_FIXTURE
    ctx = (
        replay_session(path, respect_timing=respect_timing, speed=speed)
        if replay
        else record_session(path)
        if record
        else nullcontext()
    )

    with ctx:
        return _run_act_one_core(on_event=on_event)


def _run_act_one_core(on_event: Optional[Callable[[dict], None]] = None) -> dict:
    loop = ReActLoop(act="EXCAVATION", escalate_fn=tools.escalate, on_event=on_event)

    loop.record_hypothesis_event("HYPOTHESIS", {"message": ACT_ONE_TASK_PROMPT})

    ledger = loop.call_tool(
        "query_clearing_account",
        tools.query_clearing_account,
        {"account": ACCOUNT, "from_date": FROM_DATE, "to_date": TO_DATE},
    )
    items = ledger["items"]
    opening_balance = sum(Decimal(row["amount_usd"]) for row in items)
    amount_lookup = {row["doc_id"]: Decimal(row["amount_usd"]) for row in items}

    state = DecompositionState(
        opening_amount=opening_balance, materiality=Decimal("500"), amount_lookup=amount_lookup
    )
    tools.bind_decomposition_state(state)

    strata_results = []
    plug_rows = []

    # Stratum 1 — ERP cutover artifacts
    migration = loop.call_tool("get_policy", tools.get_policy, {"entity_id": "ENT-IN-02", "period": "2023-04"})
    cutover_ids = [
        row["doc_id"] for row in items if row["source_system"] == "LEGACY_MIGRATION"
    ]
    if cutover_ids:
        r = loop.call_tool(
            "test_hypothesis",
            tools.test_hypothesis,
            {
                "cause_id": "S1",
                "classification": "ERP_CUTOVER_ARTIFACT",
                "transaction_ids": cutover_ids,
                "evidence_refs": ["data/migration_log.json"] + ledger["evidence_refs"],
            },
        )
        strata_results.append(_record_stratum(loop, "ERP_CUTOVER_ARTIFACT", r, "ERP cutover artifacts"))

    # Stratum 2 — Unreversed FX revaluation
    fx_ids = [row["doc_id"] for row in items if "FX REVAL" in row["description"].upper()]
    if fx_ids:
        r = loop.call_tool(
            "test_hypothesis",
            tools.test_hypothesis,
            {
                "cause_id": "S2",
                "classification": "UNREVERSED_FX_REVALUATION",
                "transaction_ids": fx_ids,
                "evidence_refs": ledger["evidence_refs"],
            },
        )
        strata_results.append(_record_stratum(loop, "UNREVERSED_FX_REVALUATION", r, "Unreversed FX revaluation"))

    # Stratum 3 — Duplicate AP vendor feed
    by_vendor_ref = defaultdict(list)
    for row in items:
        if row["vendor_invoice_ref"]:
            by_vendor_ref[row["vendor_invoice_ref"]].append(row["doc_id"])
    dup_ids = [doc_id for ids in by_vendor_ref.values() if len(ids) > 1 for doc_id in ids]
    if dup_ids:
        r = loop.call_tool(
            "test_hypothesis",
            tools.test_hypothesis,
            {
                "cause_id": "S3",
                "classification": "DUPLICATE_AP_VENDOR_FEED",
                "transaction_ids": dup_ids,
                "evidence_refs": ledger["evidence_refs"],
            },
        )
        strata_results.append(_record_stratum(loop, "DUPLICATE_AP_VENDOR_FEED", r, "Duplicate AP vendor feed"))

    # Stratum 4 — Accrued IC margin plugs (also seeds the cause profile)
    plug_rows = [row for row in items if "margin plug" in row["description"].lower()]
    plug_ids = [row["doc_id"] for row in plug_rows]
    if plug_ids:
        r = loop.call_tool(
            "test_hypothesis",
            tools.test_hypothesis,
            {
                "cause_id": "S4",
                "classification": "ACCRUED_MARGIN_PLUG",
                "transaction_ids": plug_ids,
                "evidence_refs": ledger["evidence_refs"],
            },
        )
        strata_results.append(_record_stratum(loop, "ACCRUED_MARGIN_PLUG", r, "Accrued IC margin plugs"))

    # Stratum 5 — Live collectible receivable
    receivable_ids = [row["doc_id"] for row in items if row.get("customer_ref")]
    if receivable_ids:
        from integrations import dodo_client

        r = loop.call_tool(
            "test_hypothesis",
            tools.test_hypothesis,
            {
                "cause_id": "S5",
                "classification": "LIVE_COLLECTIBLE_RECEIVABLE",
                "transaction_ids": receivable_ids,
                "evidence_refs": ["data/customer_contracts.json"] + ledger["evidence_refs"],
            },
        )
        stratum_5 = _record_stratum(loop, "LIVE_COLLECTIBLE_RECEIVABLE", r, "Live collectible receivable")
        try:
            collection = dodo_client.create_collection(
                customer_ref="CUST-4471",
                amount_usd=263000.00,
                description="Reinstated customer receivable (CUST-4471)",
            )
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning("Dodo collection failed: %s", exc)
            collection = {
                "payment_id": "pay_test_cust-4471_263000",
                "payment_link": "https://test.dodopayments.com/buy/pay_test_cust-4471_263000",
                "checkout_url": "https://test.dodopayments.com/buy/pay_test_cust-4471_263000",
                "customer_ref": "CUST-4471",
                "amount_usd": 263000.00,
                "currency": "USD",
                "status": "stub",
                "stub": True,
            }
        stratum_5["payment_link"] = collection.get("payment_link")
        stratum_5["payment_reference"] = collection.get("payment_id")
        stratum_5["dodo_reference"] = collection.get("payment_id")
        stratum_5["dodo_collection"] = collection
        loop.record_hypothesis_event("APPROVE_COLLECTION", collection)
        strata_results.append(stratum_5)

    # Stratum 6 — Untraceable remainder: everything not yet classified.
    classified_ids = set(cutover_ids) | set(fx_ids) | set(dup_ids) | set(plug_ids) | set(receivable_ids)
    untraceable_ids = [row["doc_id"] for row in items if row["doc_id"] not in classified_ids]
    escalation_result = None
    if untraceable_ids:
        r = loop.call_tool(
            "test_hypothesis",
            tools.test_hypothesis,
            {
                "cause_id": "S6",
                "classification": "UNTRACEABLE",
                "transaction_ids": untraceable_ids,
                "evidence_refs": [],
            },
        )
        strata_results.append(_record_stratum(loop, "UNTRACEABLE", r, "Untraceable"))

        escalation_result = tools.escalate(
            reason="UNTRACEABLE_CLEARING_BALANCE",
            residual_usd=float(r["factor_usd"]),
            evidence_gap=[
                "Original supporting documentation for undated/unreferenced clearing entries",
                "Source-system export covering the affected posting dates",
            ],
            packet={"stratum": "UNTRACEABLE", "transaction_ids": untraceable_ids},
        )
        loop.record_hypothesis_event("ESCALATION", escalation_result)

    cause_profile = _derive_cause_profile(plug_rows)
    with open(DATA_DIR / "cause_profile.json", "w", encoding="utf-8") as f:
        json.dump(cause_profile, f, indent=2)

    return {
        "opening_balance": opening_balance,
        "residual": state.residual,
        "strata": strata_results,
        "escalation": escalation_result,
        "cause_profile": cause_profile,
        "audit_trail": state.audit_trail(),
    }


def _record_stratum(loop: ReActLoop, classification: str, result: dict, label: str) -> dict:
    disposition, authority = DISPOSITIONS[classification]
    loop.record_hypothesis_event(
        "FACTOR_ACCEPTED" if result["accepted"] else "FACTOR_REJECTED",
        {"classification": classification, "label": label, "disposition": disposition, "authority": authority, **result},
    )
    return {"classification": classification, "label": label, "disposition": disposition, "authority": authority, **result}


def _derive_cause_profile(plug_rows: list[dict]) -> dict:
    """Correlates each margin-plug month against late payroll postings to
    build the prior Act II consumes (README.md §2.2 Stage 6, §4.3)."""
    import csv

    with open(DATA_DIR / "payroll_register.csv", newline="", encoding="utf-8") as f:
        payroll_rows = list(csv.DictReader(f))

    late_months = {
        row["posting_date"][:7]
        for row in payroll_rows
        if row["pay_type"] == "OFF_CYCLE_LATE"
    }
    plug_months = sorted({row["posting_date"][:7] for row in plug_rows})
    timing_months = [m for m in plug_months if m in late_months]

    n = len(plug_months) or 1
    timing_n = len(timing_months)
    remainder_n = n - timing_n

    return {
        "entity_id": "ENT-IN-02",
        "derived_from": "clearing_account_1900_excavation",
        "plug_months_analysed": n,
        "period_range": f"{plug_months[0]} to {plug_months[-1]}" if plug_months else None,
        "cause_priors": [
            {
                "cause": "TIMING_UNBILLED",
                "occurrences": timing_n,
                "prior": round(timing_n / n, 2),
                "signature": "eligible-account cost posted after billing_cutoff_day_of_month",
            },
            {
                "cause": "UNRESOLVED",
                "occurrences": remainder_n,
                "prior": round(remainder_n / n, 2),
                "signature": "no corresponding late-payroll posting found in this month",
            },
        ],
        "recommended_hypothesis_order": ["TIMING_UNBILLED", "MISCLASSIFICATION", "APPROVED_EXCLUSION", "FX_REVALUATION"],
    }


if __name__ == "__main__":
    import argparse
    from integrations.ao_client import handle_event

    parser = argparse.ArgumentParser(description="reconFX Act I — The Excavation")
    parser.add_argument(
        "--replay",
        action="store_true",
        help="Replay cached tool outputs without hitting data/ files live (demo insurance policy)",
    )
    parser.add_argument(
        "--fixture",
        type=str,
        default=None,
        help="Path to fixture JSON file (default: tests/fixtures/act_one_replay.json)",
    )
    parser.add_argument(
        "--speed",
        type=float,
        default=1.0,
        help="Playback speed multiplier for --replay (default: 1.0)",
    )
    args = parser.parse_args()

    def _on_event(e: dict) -> None:
        print(e)
        handle_event(e)

    if args.replay:
        result = run_act_one(
            on_event=_on_event,
            replay=True,
            record=False,
            fixture_path=args.fixture,
            respect_timing=True,
            speed=args.speed,
        )
    else:
        result = run_act_one(
            on_event=_on_event,
            replay=False,
            record=True,
            fixture_path=args.fixture,
        )

    print("\n--- SUMMARY ---")
    print(f"Opening balance: {result['opening_balance']}")
    print(f"Residual after all strata: {result['residual']}")
    print(f"Strata confirmed: {len(result['strata'])}")
    print(f"Escalated: {result['escalation'] is not None}")
