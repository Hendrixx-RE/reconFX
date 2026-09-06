"""Decomposition — §3.2–3.6 exclusivity, α, residual, materiality, termination.

Deterministic implementation of:
  - §3.2: Residual tracking (ρ_k = Δ₀ - Σ Fi)
  - §3.3: Exclusivity constraint (Ti ∩ Tj = ∅ for all i ≠ j)
  - §3.4: Factor quantification (Fi = α_i * Σ amount(t))
  - §3.5: Materiality gating (|Fi| >= threshold)
  - §3.6: Termination conditions (FULLY_EXPLAINED, ESCALATE, CONTINUE)
  - §3.7: Generic Act I / Act II applicability
"""

from __future__ import annotations

from typing import Any, Callable, Sequence


# --- Classification Constants (§3.4) ---
TIMING_UNBILLED: str = "TIMING_UNBILLED"
MISCLASSIFICATION: str = "MISCLASSIFICATION"
APPROVED_EXCLUSION: str = "APPROVED_EXCLUSION"
FX_REVALUATION: str = "FX_REVALUATION"
GENUINE_TP_DEVIATION: str = "GENUINE_TP_DEVIATION"

# Classifications that scale with contractual markup m_target
MARKUP_SCALED_CLASSIFICATIONS: frozenset[str] = frozenset({
    TIMING_UNBILLED,
    MISCLASSIFICATION,
    APPROVED_EXCLUSION,
})

# Classifications that represent full dollar impact (alpha = 1.0)
FIXED_ONE_CLASSIFICATIONS: frozenset[str] = frozenset({
    FX_REVALUATION,
    GENUINE_TP_DEVIATION,
})


def resolve_alpha(classification: str, m_target: float) -> float:
    """Resolve the alpha multiplier for a classification given m_target per §3.4.

    Design Choice:
    --------------
    - TIMING_UNBILLED, MISCLASSIFICATION, APPROVED_EXCLUSION scale with m_target.
      If m_target is passed as a percentage (e.g. 10.0), it is normalized to rate 0.10.
      If m_target <= 1.0, it is used directly as a rate (e.g. 0.10 or 1.0 in Act I).
    - FX_REVALUATION and GENUINE_TP_DEVIATION are fixed at 1.0 (full dollar impact).
    - Any other classification (including Act I strata) defaults to 1.0, preserving
      generic behavior across Act I and Act II without Act-II-only assumptions (§3.7).
    """
    raw_rate = float(m_target)
    rate = raw_rate / 100.0 if raw_rate > 1.0 else raw_rate

    cls_key = str(classification).strip().upper()
    if cls_key in MARKUP_SCALED_CLASSIFICATIONS:
        return rate
    elif cls_key in FIXED_ONE_CLASSIFICATIONS:
        return 1.0
    else:
        # Default to 1.0 for Act I strata or generic classifications
        return 1.0


get_alpha = resolve_alpha


class AlphaRegistry(dict):
    """Registry mapping classification names to alpha multipliers per §3.4.

    Design Choice:
    --------------
    Per §3.4, TIMING_UNBILLED, MISCLASSIFICATION, and APPROVED_EXCLUSION scale with m_target,
    while FX_REVALUATION and GENUINE_TP_DEVIATION are fixed at 1.0.
    To support multiple caller patterns:
      1. Calling as a function: `ALPHA_BY_CLASSIFICATION(m_target)` returns a `dict[str, float]`
         with all classifications resolved for the given m_target.
      2. Key indexing: `ALPHA_BY_CLASSIFICATION[classification]` returns a callable `f(m_target) -> float`.
      3. Method: `ALPHA_BY_CLASSIFICATION.resolve(classification, m_target) -> float`.
      4. Generic fallback: Unregistered classifications resolve to 1.0 (Act I uniform α = 1.0).
    """

    def __init__(self) -> None:
        super().__init__({
            TIMING_UNBILLED: lambda m: resolve_alpha(TIMING_UNBILLED, m),
            MISCLASSIFICATION: lambda m: resolve_alpha(MISCLASSIFICATION, m),
            APPROVED_EXCLUSION: lambda m: resolve_alpha(APPROVED_EXCLUSION, m),
            FX_REVALUATION: lambda m: 1.0,
            GENUINE_TP_DEVIATION: lambda m: 1.0,
        })

    def __call__(self, m_target: float) -> dict[str, float]:
        """Return resolved alpha dict for given m_target."""
        return {
            TIMING_UNBILLED: resolve_alpha(TIMING_UNBILLED, m_target),
            MISCLASSIFICATION: resolve_alpha(MISCLASSIFICATION, m_target),
            APPROVED_EXCLUSION: resolve_alpha(APPROVED_EXCLUSION, m_target),
            FX_REVALUATION: 1.0,
            GENUINE_TP_DEVIATION: 1.0,
        }

    def resolve(self, classification: str, m_target: float) -> float:
        """Resolve alpha for a specific classification and m_target."""
        return resolve_alpha(classification, m_target)

    def __getitem__(self, key: str) -> Callable[[float], float]:
        normalized_key = str(key).strip().upper()
        if normalized_key in self:
            return super().__getitem__(normalized_key)
        # Act I or custom strata fallback
        return lambda m: 1.0


ALPHA_BY_CLASSIFICATION: AlphaRegistry = AlphaRegistry()


def quantify_factor(
    transaction_ids: Sequence[str] | set[str],
    amounts_by_id: dict[str, Any],
    classification: str,
    m_target: float,
) -> float:
    """Quantify factor Fi per §3.4: Fi = α_i * Σ_{t ∈ Ti} amount(t).

    Parameters:
      transaction_ids: Iterable of transaction IDs for factor subset Ti.
      amounts_by_id: Mapping of transaction ID -> amount (or dict containing amount/amount_usd).
      classification: Stratum / hypothesis classification string.
      m_target: Target markup rate (e.g. 0.10 or 10.0; 1.0 in Act I).

    Returns:
      Fi as a float.
    """
    alpha = resolve_alpha(classification, m_target)

    # Sum distinct transaction amounts per subset Ti ⊆ T
    unique_ids = dict.fromkeys(transaction_ids)
    total_amount = 0.0
    for tid in unique_ids:
        if tid not in amounts_by_id:
            raise KeyError(f"Transaction ID '{tid}' not found in amounts_by_id")
        val = amounts_by_id[tid]
        if isinstance(val, dict):
            amt = val.get("amount_usd", val.get("amount", 0.0))
        else:
            amt = val
        total_amount += float(amt or 0.0)

    return float(alpha * total_amount)


# --- §3.3 Non-overlap Constraint (Exclusivity) ---


class ExclusivityError(Exception):
    """Raised when candidate factor transaction set intersects already-accepted sets (§3.3)."""

    def __init__(self, message: str, offending_ids: Sequence[str] | set[str] | None = None) -> None:
        super().__init__(message)
        self.offending_ids: list[str] = sorted(list(offending_ids)) if offending_ids else []


def check_exclusivity(
    new_ids: set[str] | Sequence[str],
    accepted_id_sets: Sequence[set[str] | Sequence[str]],
) -> None:
    """Validate non-overlap constraint per §3.3: Ti ∩ Tj = ∅ for all i ≠ j.

    Raises:
      ExclusivityError: If new_ids intersects any set in accepted_id_sets, listing offending IDs.
    """
    new_set = set(new_ids)
    all_offending: set[str] = set()

    for accepted in accepted_id_sets:
        intersection = new_set.intersection(set(accepted))
        if intersection:
            all_offending.update(intersection)

    if all_offending:
        offending_sorted = sorted(list(all_offending))
        raise ExclusivityError(
            f"Exclusivity constraint violated (§3.3). Offending transaction IDs already accepted: {offending_sorted}",
            offending_ids=offending_sorted,
        )


# --- §3.5 Materiality Gate ---


def passes_materiality_gate(factor_usd: float, materiality_threshold: float) -> bool:
    """Check if factor passes materiality gate per §3.5: abs(Fi) >= materiality_threshold."""
    return abs(float(factor_usd)) >= float(materiality_threshold)


# --- §3.2 Residual Tracking ---


def compute_residual(delta_0: float, accepted_factors: Sequence[float]) -> float:
    """Compute residual after accepted factors per §3.2: ρ_k = Δ₀ - Σ_{i=1}^k Fi."""
    return float(delta_0) - sum(float(f) for f in accepted_factors)


# --- §3.6 Termination ---


class TerminationStatus:
    """Termination status constants per §3.6."""

    FULLY_EXPLAINED: str = "FULLY_EXPLAINED"
    ESCALATE: str = "ESCALATE"
    CONTINUE: str = "CONTINUE"


FULLY_EXPLAINED: str = TerminationStatus.FULLY_EXPLAINED
ESCALATE: str = TerminationStatus.ESCALATE
CONTINUE: str = TerminationStatus.CONTINUE


def check_termination(
    residual: float,
    materiality_threshold: float,
    hypotheses_exhausted: bool,
    step_count: int,
    max_steps: int = 12,
) -> str:
    """Check termination conditions per §3.6:

    if abs(ρ_k) < materiality_threshold:   -> FULLY_EXPLAINED, terminate
    elif hypotheses_exhausted:            -> ESCALATE with residual and required-evidence list
    elif step_count > MAX_STEPS (12):     -> ESCALATE (loop guard)
    else:                                 -> CONTINUE
    """
    if abs(float(residual)) < float(materiality_threshold):
        return TerminationStatus.FULLY_EXPLAINED
    if hypotheses_exhausted:
        return TerminationStatus.ESCALATE
    if int(step_count) > int(max_steps):
        return TerminationStatus.ESCALATE
    return TerminationStatus.CONTINUE
