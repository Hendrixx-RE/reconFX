"""Decomposition state and exclusivity guarantee (README.md §3.2-3.5).

Public contract (do not change without updating agent/ callers):

    DecompositionState(opening_amount, materiality, target_markup=0.10, amount_lookup=None)
    DecompositionState.test_hypothesis(cause_id, classification, transaction_ids, evidence_refs) -> HypothesisResult
    DecompositionState.residual -> Decimal
    DecompositionState.is_fully_explained -> bool
    DecompositionState.audit_trail() -> list[dict]

The LLM/agent layer never supplies a dollar amount — only which
transactions belong to a hypothesis and how to classify it. This module
resolves alpha, looks up amounts, sums them, and enforces the exclusivity
and materiality gates. Section 3.3's exclusivity constraint

    T_i ∩ T_j = ∅   for all i != j

is enforced in test_hypothesis() below; it is the single most important
guarantee in the project, since it is what makes double-counting a
transaction structurally impossible rather than merely unlikely.
"""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional

# classification -> alpha (README.md §3.4). Never settable by the caller/model.
_ALPHA = {
    # Act II classifications (§3.4)
    "TIMING_UNBILLED": None,       # resolves to target_markup
    "MISCLASSIFICATION": None,     # resolves to target_markup
    "APPROVED_EXCLUSION": None,    # resolves to target_markup
    "FX_REVALUATION": Decimal("1.0"),
    "GENUINE_TP_DEVIATION": Decimal("1.0"),
    # Act I classifications (§3.7 — alpha = 1.0 for every stratum; these are
    # full dollar-amount clearing-account strata, never markup-only)
    "ERP_CUTOVER_ARTIFACT": Decimal("1.0"),
    "UNREVERSED_FX_REVALUATION": Decimal("1.0"),
    "DUPLICATE_AP_VENDOR_FEED": Decimal("1.0"),
    "ACCRUED_MARGIN_PLUG": Decimal("1.0"),
    "LIVE_COLLECTIBLE_RECEIVABLE": Decimal("1.0"),
    "UNTRACEABLE": Decimal("1.0"),
}


@dataclass
class HypothesisResult:
    accepted: bool
    cause_id: str
    classification: str
    factor_usd: Decimal
    new_residual: Decimal
    rejection_reason: Optional[str] = None
    conflicting_ids: list = field(default_factory=list)


def quantify_factor(
    classification: str,
    transaction_ids: list[str],
    amount_lookup: dict[str, Decimal],
    target_markup: Decimal = Decimal("0.10"),
    cap: Optional[Decimal] = None,
) -> Decimal:
    """Pure alpha * sum(amounts) computation with no residual side effects.

    Used for findings that sit on a separate axis from the tracked residual
    — e.g. README.md §2.4 H4: a cost misclassified into an *excluded* account
    was never part of the original deviation's transaction universe, so
    quantifying its markup impact must not decrement the tracked residual.
    It is a recovery finding, not a factor.
    """
    if classification not in _ALPHA:
        raise ValueError(f"Unknown classification: {classification}")
    fixed = _ALPHA[classification]
    alpha = fixed if fixed is not None else target_markup
    missing = [t for t in transaction_ids if t not in amount_lookup]
    if missing:
        raise KeyError(f"No amount on file for transaction id(s): {missing}")
    total = sum((Decimal(amount_lookup[t]) for t in transaction_ids), Decimal("0"))
    factor = alpha * total
    if cap is not None:
        factor = min(factor, Decimal(str(cap)))
    return factor


class DecompositionState:
    """Owns the residual and the accepted transaction sets.
    This class is the audit guarantee. Treat it as such."""

    def __init__(
        self,
        opening_amount: Decimal,
        materiality: Decimal,
        target_markup: Decimal = Decimal("0.10"),
        amount_lookup: Optional[dict[str, Decimal]] = None,
    ):
        """
        amount_lookup maps transaction_id -> Decimal(amount_usd), sourced
        from data/ (entity_gl.csv, clearing_ledger.csv, ...) by whoever
        constructs this state. The engine looks amounts up itself; the
        caller/LLM never supplies a dollar figure.
        """
        self._residual = Decimal(opening_amount)
        self._materiality = Decimal(materiality)
        self._target_markup = Decimal(target_markup)
        self._amount_lookup = amount_lookup or {}
        self._accepted_sets: dict[str, set[str]] = {}
        self._trail: list[dict] = []

    def _alpha_for(self, classification: str) -> Decimal:
        if classification not in _ALPHA:
            raise ValueError(f"Unknown classification: {classification}")
        fixed = _ALPHA[classification]
        return fixed if fixed is not None else self._target_markup

    def test_hypothesis(
        self,
        cause_id: str,
        classification: str,
        transaction_ids: list[str],
        evidence_refs: list[str],
        cap: Optional[Decimal] = None,
    ) -> HypothesisResult:
        txn_set = set(transaction_ids)

        # 1. Exclusivity: reject if this set intersects any accepted set.
        for other_set in self._accepted_sets.values():
            overlap = txn_set & other_set
            if overlap:
                result = HypothesisResult(
                    accepted=False,
                    cause_id=cause_id,
                    classification=classification,
                    factor_usd=Decimal("0"),
                    new_residual=self._residual,
                    rejection_reason="TRANSACTION_SET_OVERLAP",
                    conflicting_ids=sorted(overlap),
                )
                self._log(result, evidence_refs)
                return result

        # 2. Resolve alpha from classification (never from caller input).
        alpha = self._alpha_for(classification)

        # 3. factor = alpha * sum(amounts of transaction_ids), looked up internally.
        missing = [t for t in transaction_ids if t not in self._amount_lookup]
        if missing:
            raise KeyError(f"No amount on file for transaction id(s): {missing}")
        total = sum((Decimal(self._amount_lookup[t]) for t in transaction_ids), Decimal("0"))
        factor = alpha * total
        if cap is not None:
            factor = min(factor, Decimal(str(cap)))

        # 4. Materiality gate.
        if abs(factor) < self._materiality:
            result = HypothesisResult(
                accepted=False,
                cause_id=cause_id,
                classification=classification,
                factor_usd=factor,
                new_residual=self._residual,
                rejection_reason="BELOW_MATERIALITY",
            )
            self._log(result, evidence_refs)
            return result

        # 5. Accept: record set, decrement residual. Reject rather than let
        #    the residual go negative (over-explanation, §10.2 attack #9).
        new_residual = self._residual - factor
        if new_residual < 0:
            result = HypothesisResult(
                accepted=False,
                cause_id=cause_id,
                classification=classification,
                factor_usd=factor,
                new_residual=self._residual,
                rejection_reason="OVER_ATTRIBUTION",
            )
            self._log(result, evidence_refs)
            return result

        self._accepted_sets[cause_id] = txn_set
        self._residual = new_residual
        result = HypothesisResult(
            accepted=True,
            cause_id=cause_id,
            classification=classification,
            factor_usd=factor,
            new_residual=new_residual,
        )
        self._log(result, evidence_refs)
        return result

    def _log(self, result: HypothesisResult, evidence_refs: list[str]) -> None:
        self._trail.append(
            {
                "cause_id": result.cause_id,
                "classification": result.classification,
                "accepted": result.accepted,
                "factor_usd": result.factor_usd,
                "residual_after": result.new_residual,
                "rejection_reason": result.rejection_reason,
                "evidence_refs": evidence_refs,
            }
        )

    @property
    def residual(self) -> Decimal:
        return self._residual

    @property
    def is_fully_explained(self) -> bool:
        return abs(self._residual) < self._materiality

    def audit_trail(self) -> list[dict]:
        return list(self._trail)
