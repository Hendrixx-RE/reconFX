"""Act II baseline computation (PLAN.md §3.1).

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
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Optional

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


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
    eligible_base = sum((Decimal(row["amount_usd"]) for row in gl_rows), Decimal("0"))

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
