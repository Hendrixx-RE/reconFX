"""Typed event builders and schema matching README.md Appendix B.

Allowed event types:
  TOOL_CALL | HYPOTHESIS | FACTOR_ACCEPTED | FACTOR_REJECTED |
  RECOVERY_FOUND | DISPOSITION | ESCALATION | DECISION | COST

Every event on the WebSocket adheres to:
{
  "event_type": "...",
  "act": "EXCAVATION | INVESTIGATION",
  "timestamp": "2026-03-31T10:14:22Z",
  "step": 4,
  "payload": { ... }
}
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Literal, Optional, Set, Union
from pydantic import BaseModel, Field, field_validator


EventType = Literal[
    "TOOL_CALL",
    "HYPOTHESIS",
    "FACTOR_ACCEPTED",
    "FACTOR_REJECTED",
    "RECOVERY_FOUND",
    "DISPOSITION",
    "ESCALATION",
    "DECISION",
    "COST",
]

VALID_EVENT_TYPES: Set[str] = {
    "TOOL_CALL",
    "HYPOTHESIS",
    "FACTOR_ACCEPTED",
    "FACTOR_REJECTED",
    "RECOVERY_FOUND",
    "DISPOSITION",
    "ESCALATION",
    "DECISION",
    "COST",
}

# Mapping of known aliases/variants to canonical Appendix B event types
EVENT_TYPE_ALIASES: Dict[str, str] = {
    "APPROVE_COLLECTION": "DECISION",
    "APPROVE_TRUEUP": "DECISION",
    "CONTROLLER_DECISION": "DECISION",
    "RECORD_DECISION": "DECISION",
}


def sanitize_value(val: Any) -> Any:
    """Recursively convert Decimals to floats and ensure JSON serializability."""
    if isinstance(val, Decimal):
        return float(val)
    if isinstance(val, datetime):
        return val.isoformat()
    if isinstance(val, dict):
        return {str(k): sanitize_value(v) for k, v in val.items()}
    if isinstance(val, (list, tuple, set)):
        return [sanitize_value(v) for v in val]
    if hasattr(val, "model_dump") and callable(val.model_dump):
        return sanitize_value(val.model_dump())
    if hasattr(val, "__dict__") and not isinstance(val, type):
        return sanitize_value(vars(val))
    return val


class ReconEvent(BaseModel):
    """Pydantic model representing an Appendix B event."""

    event_type: str
    act: str = "INVESTIGATION"
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    step: int = 0
    payload: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("event_type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        canonical = EVENT_TYPE_ALIASES.get(v, v)
        if canonical not in VALID_EVENT_TYPES:
            raise ValueError(
                f"Invalid event_type '{v}'. Must be one of {sorted(VALID_EVENT_TYPES)}"
            )
        return canonical

    @field_validator("payload", mode="before")
    @classmethod
    def clean_payload(cls, v: Any) -> Dict[str, Any]:
        if not isinstance(v, dict):
            return {"data": sanitize_value(v)}
        return sanitize_value(v)


def normalize_event(raw_event: Union[Dict[str, Any], ReconEvent]) -> Dict[str, Any]:
    """Validates and normalizes an event dictionary emitted by agent/loop.py or elsewhere.

    Ensures event_type matches Appendix B, numbers are JSON-safe, and fields are complete.
    """
    if isinstance(raw_event, ReconEvent):
        raw_dict = raw_event.model_dump()
    elif isinstance(raw_event, dict):
        raw_dict = dict(raw_event)
    else:
        raise TypeError(f"Expected dict or ReconEvent, got {type(raw_event).__name__}")

    raw_type = str(raw_dict.get("event_type", "")).strip()
    canonical_type = EVENT_TYPE_ALIASES.get(raw_type, raw_type)
    if canonical_type not in VALID_EVENT_TYPES:
        raise ValueError(
            f"Invalid event_type '{raw_type}'. Must be one of {sorted(VALID_EVENT_TYPES)}"
        )

    act = str(raw_dict.get("act", "INVESTIGATION")).strip() or "INVESTIGATION"
    step = int(raw_dict.get("step", 0))

    timestamp = raw_dict.get("timestamp")
    if not timestamp:
        timestamp = datetime.now(timezone.utc).isoformat()
    elif isinstance(timestamp, datetime):
        timestamp = timestamp.isoformat()
    else:
        timestamp = str(timestamp)

    payload = raw_dict.get("payload", {})
    if not isinstance(payload, dict):
        payload = {"value": payload}
    payload = sanitize_value(payload)

    # Preserve special action notes if aliased
    if raw_type in EVENT_TYPE_ALIASES and "action" not in payload:
        payload["action"] = raw_type
        if "decision_type" not in payload:
            payload["decision_type"] = raw_type

    return {
        "event_type": canonical_type,
        "act": act,
        "timestamp": timestamp,
        "step": step,
        "payload": payload,
    }


def validate_event(raw_event: Union[Dict[str, Any], ReconEvent]) -> ReconEvent:
    """Validates an event and returns a strongly-typed ReconEvent model."""
    norm = normalize_event(raw_event)
    return ReconEvent(**norm)


def build_event(
    event_type: str,
    act: str = "INVESTIGATION",
    step: int = 0,
    payload: Optional[Dict[str, Any]] = None,
    timestamp: Optional[str] = None,
) -> Dict[str, Any]:
    """Generic builder for Appendix B events."""
    raw = {
        "event_type": event_type,
        "act": act,
        "step": step,
        "timestamp": timestamp or datetime.now(timezone.utc).isoformat(),
        "payload": payload or {},
    }
    return normalize_event(raw)


def build_tool_call_event(
    tool_name: str,
    kwargs: Dict[str, Any],
    result: Any,
    act: str = "INVESTIGATION",
    step: int = 0,
    **extra: Any,
) -> Dict[str, Any]:
    """Builder for TOOL_CALL events."""
    payload = {
        "tool_name": tool_name,
        "kwargs": sanitize_value(kwargs),
        "result": sanitize_value(result),
        **extra,
    }
    return build_event(event_type="TOOL_CALL", act=act, step=step, payload=payload)


def build_hypothesis_event(
    message: str,
    act: str = "INVESTIGATION",
    step: int = 0,
    payload: Optional[Dict[str, Any]] = None,
    **extra: Any,
) -> Dict[str, Any]:
    """Builder for HYPOTHESIS events."""
    body = {"message": message, **(payload or {}), **extra}
    return build_event(event_type="HYPOTHESIS", act=act, step=step, payload=body)


def build_factor_accepted_event(
    cause_id: str,
    label: str,
    classification: str,
    factor_usd: float,
    residual_after: float,
    act: str = "INVESTIGATION",
    step: int = 0,
    transaction_ids: Optional[List[str]] = None,
    evidence_refs: Optional[List[str]] = None,
    disposition: Optional[str] = None,
    **extra: Any,
) -> Dict[str, Any]:
    """Builder for FACTOR_ACCEPTED events."""
    payload = {
        "cause_id": cause_id,
        "label": label,
        "classification": classification,
        "factor_usd": float(factor_usd),
        "residual_after": float(residual_after),
        "transaction_ids": transaction_ids or [],
        "evidence_refs": evidence_refs or [],
        "disposition": disposition,
        **extra,
    }
    return build_event(event_type="FACTOR_ACCEPTED", act=act, step=step, payload=payload)


def build_factor_rejected_event(
    cause_id: str,
    rejection_reason: str,
    act: str = "INVESTIGATION",
    step: int = 0,
    hypothesis: Optional[str] = None,
    computed_impact_usd: Optional[float] = None,
    threshold_usd: Optional[float] = None,
    **extra: Any,
) -> Dict[str, Any]:
    """Builder for FACTOR_REJECTED events."""
    payload = {
        "cause_id": cause_id,
        "rejection_reason": rejection_reason,
        "hypothesis": hypothesis,
        "computed_impact_usd": float(computed_impact_usd) if computed_impact_usd is not None else None,
        "threshold_usd": float(threshold_usd) if threshold_usd is not None else None,
        **extra,
    }
    return build_event(event_type="FACTOR_REJECTED", act=act, step=step, payload=payload)


def build_recovery_found_event(
    cause_id: str,
    label: str,
    entitlement_impact_usd: float,
    act: str = "INVESTIGATION",
    step: int = 0,
    amount_usd: Optional[float] = None,
    proposed_entry: Optional[str] = None,
    **extra: Any,
) -> Dict[str, Any]:
    """Builder for RECOVERY_FOUND events."""
    payload = {
        "cause_id": cause_id,
        "label": label,
        "entitlement_impact_usd": float(entitlement_impact_usd),
        "amount_usd": float(amount_usd) if amount_usd is not None else None,
        "proposed_entry": proposed_entry,
        **extra,
    }
    return build_event(event_type="RECOVERY_FOUND", act=act, step=step, payload=payload)


def build_disposition_event(
    classification: str,
    disposition: str,
    authority: Optional[str] = None,
    act: str = "INVESTIGATION",
    step: int = 0,
    **extra: Any,
) -> Dict[str, Any]:
    """Builder for DISPOSITION events."""
    payload = {
        "classification": classification,
        "disposition": disposition,
        "authority": authority,
        **extra,
    }
    return build_event(event_type="DISPOSITION", act=act, step=step, payload=payload)


def build_escalation_event(
    reason: str,
    residual_usd: float,
    evidence_gap: List[str],
    packet: Optional[Dict[str, Any]] = None,
    act: str = "INVESTIGATION",
    step: int = 0,
    **extra: Any,
) -> Dict[str, Any]:
    """Builder for ESCALATION events."""
    payload = {
        "reason": reason,
        "residual_usd": float(residual_usd),
        "evidence_gap": evidence_gap,
        "packet": sanitize_value(packet or {}),
        **extra,
    }
    return build_event(event_type="ESCALATION", act=act, step=step, payload=payload)


def build_decision_event(
    decision_type: str,
    actor: str = "controller",
    reference: Optional[str] = None,
    act: str = "INVESTIGATION",
    step: int = 0,
    **extra: Any,
) -> Dict[str, Any]:
    """Builder for DECISION events."""
    payload = {
        "decision_type": decision_type,
        "actor": actor,
        "reference": reference,
        **extra,
    }
    return build_event(event_type="DECISION", act=act, step=step, payload=payload)


def build_cost_event(
    cost_summary: Dict[str, Any],
    act: str = "INVESTIGATION",
    step: int = 0,
    **extra: Any,
) -> Dict[str, Any]:
    """Builder for COST events."""
    payload = {
        **sanitize_value(cost_summary),
        **extra,
    }
    return build_event(event_type="COST", act=act, step=step, payload=payload)
