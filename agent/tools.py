"""The 7 tools available to the reconFX agent (README.md §5.2).

Every tool is a thin wrapper: it reads from data/ and delegates arithmetic
to engine/. It returns a JSON-serialisable dict with an `evidence_refs`
list. None of these functions may return a value that is trusted as a
final dollar figure without going through test_hypothesis(), which is the
only tool backed by engine.decomposition.DecompositionState.

Each tool is wrapped with a no-op Neatlogs span decorator here so Phase 4
can swap in the real `neatlogs.span(kind="TOOL")` decorator without
touching call sites.
"""

import csv
import json
from decimal import Decimal
from functools import wraps
from pathlib import Path
from typing import Optional

from engine.decomposition import DecompositionState, HypothesisResult

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def span(kind: str):
    """Placeholder for @neatlogs.span(kind=...). Phase 4 replaces the body
    with real instrumentation; call sites do not change."""
    import os

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if os.environ.get("NEATLOGS_API_KEY"):
                try:
                    import neatlogs

                    try:
                        import integrations.neatlogs_setup as nsetup

                        if not getattr(nsetup, "_initialized", False):
                            nsetup.init_neatlogs()
                    except ImportError:
                        pass
                    if hasattr(neatlogs, "span"):
                        return neatlogs.span(kind=kind)(fn)(*args, **kwargs)
                except Exception as exc:
                    tb = exc.__traceback__
                    while tb:
                        if tb.tb_frame.f_code is fn.__code__:
                            raise
                        tb = tb.tb_next
            try:
                return fn(*args, **kwargs)
            except Exception:
                raise

        return wrapper

    return decorator


def _read_csv(name: str) -> list[dict]:
    path = DATA_DIR / name
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _read_json(name: str):
    path = DATA_DIR / name
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _to_decimal(row: dict, field: str) -> Decimal:
    return Decimal(row[field]) if row.get(field) not in (None, "") else Decimal("0")


# ---------------------------------------------------------------------------
# 1. get_policy
# ---------------------------------------------------------------------------
@span(kind="TOOL")
def get_policy(entity_id: str, period: str) -> dict:
    """TP policy, contract terms, GL mappings, precedence order, materiality."""
    policy = _read_json("tp_policy.json")
    contract = _read_json("intercompany_contract.json")
    return {
        "policy": policy,
        "contract": contract,
        "evidence_refs": ["data/tp_policy.json", "data/intercompany_contract.json"],
    }


# ---------------------------------------------------------------------------
# 2. query_gl
# ---------------------------------------------------------------------------
@span(kind="TOOL")
def query_gl(
    entity_id: str,
    period_start: str,
    period_end: str,
    gl_accounts: Optional[list[str]] = None,
    cost_centers: Optional[list[str]] = None,
    description_contains: Optional[str] = None,
) -> dict:
    """GL line items filtered by date range and optional descriptive filters."""
    rows = _read_csv("entity_gl.csv")
    out = []
    for row in rows:
        if not (period_start <= row["posting_date"] <= period_end):
            continue
        if gl_accounts and row["gl_account"] not in gl_accounts:
            continue
        if cost_centers and row["cost_center"] not in cost_centers:
            continue
        if description_contains and description_contains.lower() not in row["description"].lower():
            continue
        out.append(row)
    return {
        "items": out,
        "evidence_refs": [f"data/entity_gl.csv#{r['doc_id']}" for r in out],
    }


# ---------------------------------------------------------------------------
# 3. query_payroll
# ---------------------------------------------------------------------------
@span(kind="TOOL")
def query_payroll(entity_id: str, period: str) -> dict:
    """Payroll runs with service period AND posting date, so the caller can
    derive the timing gap itself."""
    rows = _read_csv("payroll_register.csv")
    out = [r for r in rows if r["service_period_start"].startswith(period)]
    return {
        "items": out,
        "evidence_refs": [f"data/payroll_register.csv#{r['payroll_id']}" for r in out],
    }


# ---------------------------------------------------------------------------
# 4. query_approvals
# ---------------------------------------------------------------------------
@span(kind="TOOL")
def query_approvals(
    entity_id: str, period: str, gl_account: Optional[str] = None
) -> dict:
    """Policy exception memos, including narrative text and doc links."""
    rows = _read_json("policy_exceptions.json")
    out = [
        r
        for r in rows
        if r["entity_id"] == entity_id
        and r["effective_period"] == period
        and (gl_account is None or gl_account in r["applies_to_gl_accounts"])
    ]
    return {
        "items": out,
        "evidence_refs": [
            f"data/policy_exceptions.json#{r['exception_id']}" for r in out
        ]
        + [r["documentation_link"] for r in out],
    }


# ---------------------------------------------------------------------------
# 5. query_clearing_account
# ---------------------------------------------------------------------------
@span(kind="TOOL")
def query_clearing_account(account: str, from_date: str, to_date: str) -> dict:
    """Act I. Open items in the clearing account across the full history."""
    rows = _read_csv("clearing_ledger.csv")
    out = [
        r
        for r in rows
        if r["account"] == account and from_date <= r["posting_date"] <= to_date
    ]
    return {
        "items": out,
        "evidence_refs": [f"data/clearing_ledger.csv#{r['doc_id']}" for r in out],
    }


# ---------------------------------------------------------------------------
# 6. test_hypothesis — THE GATE
# ---------------------------------------------------------------------------
_STATE: Optional[DecompositionState] = None


def bind_decomposition_state(state: DecompositionState) -> None:
    """Called once per run by act_one.py / act_two.py before the loop starts."""
    global _STATE
    _STATE = state


@span(kind="DECISION")
def test_hypothesis(
    cause_id: str,
    classification: str,
    transaction_ids: list[str],
    evidence_refs: list[str],
) -> dict:
    """Validates exclusivity against accepted sets, applies alpha by
    classification, computes the factor deterministically, applies the
    materiality gate, updates the residual. Returns a dict, never a bare
    number, so callers cannot mistake this for a value they computed."""
    if _STATE is None:
        raise RuntimeError("DecompositionState not bound — call bind_decomposition_state() first")

    result: HypothesisResult = _STATE.test_hypothesis(
        cause_id=cause_id,
        classification=classification,
        transaction_ids=transaction_ids,
        evidence_refs=evidence_refs,
    )
    return {
        "accepted": result.accepted,
        "factor_usd": str(result.factor_usd),
        "new_residual": str(result.new_residual),
        "rejection_reason": result.rejection_reason,
        "conflicting_ids": result.conflicting_ids,
    }


# ---------------------------------------------------------------------------
# 7a. draft_journal_entry
# ---------------------------------------------------------------------------
@span(kind="TOOL")
def draft_journal_entry(
    entry_type: str,
    lines: list[dict],
    supporting_evidence: list[str],
    requires_approval: bool,
) -> dict:
    """Structured JE payload. Never posts. Status is always DRAFT."""
    total_debit = sum(Decimal(str(l.get("debit", 0))) for l in lines)
    total_credit = sum(Decimal(str(l.get("credit", 0))) for l in lines)
    if total_debit != total_credit:
        raise ValueError(
            f"Unbalanced journal entry: debits {total_debit} != credits {total_credit}"
        )
    return {
        "entry_type": entry_type,
        "status": "DRAFT",
        "lines": lines,
        "supporting_evidence": supporting_evidence,
        "requires_approval": requires_approval,
    }


# ---------------------------------------------------------------------------
# 7b. escalate
# ---------------------------------------------------------------------------
@span(kind="DECISION")
def escalate(reason: str, residual_usd: float, evidence_gap: list[str], packet: dict) -> dict:
    """Halts execution. Emits the controller packet naming exactly what
    evidence would close the gap."""
    return {
        "halted": True,
        "reason": reason,
        "residual_usd": str(residual_usd),
        "evidence_gap": evidence_gap,
        "packet": packet,
    }
