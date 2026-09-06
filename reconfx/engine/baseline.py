"""Baseline computation — §3.1 Act II baseline.

Computes the naive cost base (E_naive), contractual target profit,
billed cost base (B), recognised profit, effective markup, and
the initial deviation (Δ₀).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence
import pandas as pd


@dataclass
class BaselineResult:
    """Act II baseline reconciliation result per §3.1."""

    e_naive: float
    target_profit: float
    billed_cost_base: float
    recognised_revenue: float
    recognised_profit: float
    effective_markup: float
    delta_0: float


def compute_e_naive(
    gl_lines: list[dict[str, Any]] | pd.DataFrame,
    eligible_gl_accounts: Sequence[str],
    eligible_cost_centers: Sequence[str],
) -> float:
    """Compute naive cost base E_naive per §3.1.

    E_naive = all GL lines where gl_account ∈ eligible_gl_accounts
              AND cost_center ∈ eligible_cost_centers.
    """
    if isinstance(gl_lines, pd.DataFrame):
        records = gl_lines.to_dict("records")
    else:
        records = gl_lines

    eligible_accounts_set = {str(a).strip() for a in eligible_gl_accounts}
    eligible_cc_set = {str(c).strip() for c in eligible_cost_centers}

    total = 0.0
    for row in records:
        acct = str(row.get("gl_account", "")).strip()
        cc = str(row.get("cost_center", "")).strip()
        if acct in eligible_accounts_set and cc in eligible_cc_set:
            raw_amt = row.get("amount_usd", row.get("amount", 0.0))
            total += float(raw_amt or 0.0)

    return float(total)


def compute_baseline(
    gl_lines: list[dict[str, Any]] | pd.DataFrame,
    invoice_lines: list[dict[str, Any]] | pd.DataFrame,
    recognised_revenue: float,
    target_markup_percent: float,
    eligible_gl_accounts: Sequence[str],
    eligible_cost_centers: Sequence[str],
) -> BaselineResult:
    """Compute full Act II baseline reconciliation per §3.1.

    Per §3.1:
      m_target          = contractual markup rate (0.10)
      target_profit     = m_target * E_naive
      B                 = sum(billed_amount_usd where recharge_flag == 'Y')
      recognised_profit = R - B
      effective_markup  = recognised_profit / E_naive
      delta_0           = target_profit - recognised_profit
    """
    e_naive = compute_e_naive(gl_lines, eligible_gl_accounts, eligible_cost_centers)

    # Normalize markup rate: handles both percentage (e.g. 10.0) and decimal fraction (e.g. 0.10)
    raw_markup = float(target_markup_percent)
    m_target = raw_markup / 100.0 if raw_markup > 1.0 else raw_markup

    target_profit = float(m_target * e_naive)

    if isinstance(invoice_lines, pd.DataFrame):
        inv_records = invoice_lines.to_dict("records")
    else:
        inv_records = invoice_lines

    billed_cost_base = 0.0
    for row in inv_records:
        recharge_flag = str(row.get("recharge_flag", "")).strip().upper()
        if recharge_flag == "Y":
            raw_amt = row.get("billed_amount_usd", row.get("billed_amount", row.get("amount", 0.0)))
            billed_cost_base += float(raw_amt or 0.0)

    r = float(recognised_revenue)
    recognised_profit = r - billed_cost_base
    effective_markup = recognised_profit / e_naive if e_naive != 0.0 else 0.0
    delta_0 = target_profit - recognised_profit

    return BaselineResult(
        e_naive=e_naive,
        target_profit=target_profit,
        billed_cost_base=billed_cost_base,
        recognised_revenue=r,
        recognised_profit=recognised_profit,
        effective_markup=effective_markup,
        delta_0=delta_0,
    )
