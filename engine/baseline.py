"""Act II baseline computation (README.md §3.1).

    m_target = contractual markup rate
    E_naive  = cost base as computed by a standard OTP monitor: all GL lines
               where gl_account in eligible_gl_accounts AND
               cost_center in eligible_cost_centers
    B        = cost base actually billed, from intercompany_invoice_lines.csv
    R        = intercompany revenue actually recorded

    target_profit     = m_target * E_naive
    recognised_profit = R - B
    deviation         = target_profit - recognised_profit
    effective_markup  = recognised_profit / E_naive

All four are recomputed from source here, never trusted from an alert —
that is the point of this module. Decimal throughout; floats are never
used for a dollar figure anywhere in this codebase.
"""

import csv
import json
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Optional

from engine.journal import JournalEntry, draft_reversal

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


@dataclass(frozen=True)
class DuplicateDetectionResult:
    has_duplicates: bool
    duplicate_ids: list[str]
    clean_rows: list[dict]
    duplicate_rows: list[dict]
    reversal_entries: list[JournalEntry]


def detect_duplicate_gl_rows(rows: list[dict]) -> DuplicateDetectionResult:
    """Duplicate detector (§10.2 attack #7):
    Checks for duplicate doc_ids in GL rows.
    When duplicates are found, fires, drafts reversal journal entries, and excludes duplicates from the base.
    """
    seen_ids = set()
    dup_ids = set()
    for r in rows:
        doc_id = r["doc_id"]
        if doc_id in seen_ids:
            dup_ids.add(doc_id)
        seen_ids.add(doc_id)

    clean_rows: list[dict] = []
    duplicate_rows: list[dict] = []
    reversals: list[JournalEntry] = []
    seen_clean = set()

    for r in rows:
        doc_id = r["doc_id"]
        if doc_id in dup_ids:
            if doc_id not in seen_clean:
                seen_clean.add(doc_id)
                clean_rows.append(r)
            else:
                duplicate_rows.append(r)
                reversals.append(
                    draft_reversal(
                        amount=Decimal(str(r["amount_usd"])),
                        account=r["gl_account"],
                        offset_account="1900",
                        description=f"Duplicate GL doc {doc_id}: {r.get('description', '')}",
                        entity=r.get("entity_id", ""),
                        evidence=[f"data/entity_gl.csv#{doc_id}"],
                    )
                )
        else:
            clean_rows.append(r)

    return DuplicateDetectionResult(
        has_duplicates=bool(dup_ids),
        duplicate_ids=sorted(dup_ids),
        clean_rows=clean_rows,
        duplicate_rows=duplicate_rows,
        reversal_entries=reversals,
    )


@dataclass(frozen=True)
class Baseline:
    entity_id: str
    period: str
    eligible_base: Decimal
    target_markup: Decimal
    target_profit: Decimal
    billed_base: Decimal
    recorded_revenue: Decimal
    recognised_profit: Decimal
    effective_markup: Decimal
    deviation: Decimal
    materiality: Decimal


def _load_policy() -> dict:
    with open(DATA_DIR / "tp_policy.json", encoding="utf-8") as f:
        return json.load(f)


def _load_gl_rows() -> list[dict]:
    with open(DATA_DIR / "entity_gl.csv", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _load_invoice_lines() -> list[dict]:
    with open(DATA_DIR / "intercompany_invoice_lines.csv", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _load_invoices() -> list[dict]:
    with open(DATA_DIR / "intercompany_invoices.csv", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _in_period(posting_date: str, period: str) -> bool:
    return posting_date.startswith(period)


def compute_baseline(entity_id: str, period: str, precision: int = 4) -> Baseline:
    policy = _load_policy()
    eligible_gl_accounts = set(policy["eligible_gl_accounts"])
    eligible_cost_centers = set(policy["eligible_cost_centers"])
    m_target = Decimal(str(policy["target_markup_percent"])) / Decimal("100")
    materiality = Decimal(str(policy["materiality_threshold_usd"]))

    gl_rows = [
        row
        for row in _load_gl_rows()
        if _in_period(row["posting_date"], period)
        and row["gl_account"] in eligible_gl_accounts
        and row["cost_center"] in eligible_cost_centers
    ]
    dup_res = detect_duplicate_gl_rows(gl_rows)
    clean_gl_rows = dup_res.clean_rows
    eligible_base = sum((Decimal(row["amount_usd"]) for row in clean_gl_rows), Decimal("0"))

    invoice_lines = [
        row for row in _load_invoice_lines() if row["recharge_flag"] == "Y"
    ]
    billed_base = sum((Decimal(row["billed_amount_usd"]) for row in invoice_lines), Decimal("0"))

    invoices = [row for row in _load_invoices() if _in_period(row["invoice_date"], period)]
    recorded_revenue = sum((Decimal(row["total_billed_usd"]) for row in invoices), Decimal("0"))

    target_profit = m_target * eligible_base
    recognised_profit = recorded_revenue - billed_base
    deviation = target_profit - recognised_profit
    effective_markup = (
        (recognised_profit / eligible_base).quantize(Decimal("1." + "0" * precision), rounding=ROUND_HALF_UP)
        if eligible_base
        else Decimal("0")
    )

    return Baseline(
        entity_id=entity_id,
        period=period,
        eligible_base=eligible_base,
        target_markup=m_target,
        target_profit=target_profit,
        billed_base=billed_base,
        recorded_revenue=recorded_revenue,
        recognised_profit=recognised_profit,
        effective_markup=effective_markup,
        deviation=deviation,
        materiality=materiality,
    )


def check_mapping_conflict(gl_row: dict, policy: dict) -> dict:
    """Flags conflict between GL description and account mapping (§10.2 attack #3).
    Applies document precedence order from policy and records the override explicitly.
    """
    desc = gl_row.get("description", "").lower()
    account = gl_row.get("gl_account", "")
    account_desc = gl_row.get("account_description", "").lower()
    excluded_accounts = set(policy.get("excluded_gl_accounts", []))
    eligible_accounts = set(policy.get("eligible_gl_accounts", []))

    indicates_rechargeable = any(
        kw in desc or kw in account_desc
        for kw in ["rechargeable", "recharge", "engineering", "devops", "cloud"]
    )
    is_excluded = account in excluded_accounts or (eligible_accounts and account not in eligible_accounts)

    has_conflict = bool(indicates_rechargeable and is_excluded)
    if not has_conflict:
        return {"has_conflict": False}

    precedence = policy.get(
        "document_precedence",
        [
            "APPROVED_POLICY_EXCEPTION_MEMO",
            "INTERCOMPANY_CONTRACT",
            "TP_POLICY_GL_MAPPING",
            "GL_LINE_DESCRIPTION",
        ],
    )

    mapping_rank = precedence.index("TP_POLICY_GL_MAPPING") if "TP_POLICY_GL_MAPPING" in precedence else 999
    desc_rank = precedence.index("GL_LINE_DESCRIPTION") if "GL_LINE_DESCRIPTION" in precedence else 999

    if mapping_rank < desc_rank:
        winner = "TP_POLICY_GL_MAPPING"
        overridden = "GL_LINE_DESCRIPTION"
    else:
        winner = "GL_LINE_DESCRIPTION"
        overridden = "TP_POLICY_GL_MAPPING"

    override_record = f"{winner} overrides {overridden}"

    return {
        "has_conflict": True,
        "conflict_type": "MAPPING_CONFLICT",
        "doc_id": gl_row.get("doc_id"),
        "account": account,
        "description": gl_row.get("description"),
        "resolved_by": winner,
        "overridden": overridden,
        "override_record": override_record,
        "treatment": "EXCLUDE_FROM_BASE" if winner == "TP_POLICY_GL_MAPPING" else "INCLUDE_IN_BASE",
    }


def check_policy_effective_date(policy: dict, posting_date: str) -> bool:
    """Checks whether posting date falls within policy effective date range (§10.2 attack #4)."""
    start = policy.get("effective_date", "")
    end = policy.get("expiry_date", "9999-12-31")
    return start <= posting_date <= end


def get_effective_policy_markup(policy: dict, posting_date: str) -> Decimal:
    """Checks posting date against policy effective range before applying a rate (§10.2 attack #4)."""
    if not check_policy_effective_date(policy, posting_date):
        raise ValueError(
            f"Posting date {posting_date} outside policy effective range "
            f"({policy.get('effective_date')} to {policy.get('expiry_date')})"
        )
    return Decimal(str(policy["target_markup_percent"])) / Decimal("100")

