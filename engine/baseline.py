"""
STUB — Phase 2 owner replaces this with the real implementation.

Contract (must not change without updating agent/ callers):
    compute_baseline(entity_id: str, period: str) -> Baseline

Real version computes eligible_base, target_profit, billed_base, recognised_profit,
effective_markup and deviation from data/entity_gl.csv, data/tp_policy.json and
data/intercompany_invoice_lines.csv (see PLAN.md §3.1). This stub returns the
frozen canonical numbers for ENT-IN-02 / 2026-03 (PLAN.md §4.1) so agent/ has a
real object to call while Phase 2 is being built.
"""

from dataclasses import dataclass
from decimal import Decimal


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


_CANONICAL = {
    ("ENT-IN-02", "2026-03"): Baseline(
        entity_id="ENT-IN-02",
        period="2026-03",
        eligible_base=Decimal("2760000.00"),
        target_markup=Decimal("0.10"),
        target_profit=Decimal("276000.00"),
        billed_base=Decimal("2370000.00"),
        recorded_revenue=Decimal("2602000.00"),
        recognised_profit=Decimal("232000.00"),
        effective_markup=Decimal("0.0841"),
        deviation=Decimal("44000.00"),
        materiality=Decimal("500.00"),
    )
}


def compute_baseline(entity_id: str, period: str) -> Baseline:
    key = (entity_id, period)
    if key not in _CANONICAL:
        raise NotImplementedError(
            f"No stub baseline for {key}. This is a Phase 2 stub covering only "
            f"the canonical PLAN.md §4.1 case."
        )
    return _CANONICAL[key]
