"""STUB — Phase 2 owner may replace/refine. Maps classification -> (treatment,
requires_approval, escalation_destination) per PLAN.md §2.4 / §4.2.

agent/act_one.py and agent/act_two.py currently keep their own local
DISPOSITIONS maps for the strata/factor labels used in the narrative; this
module is the shared, importable version other layers (api/, ui/) can read
from once Phase 2 finalizes it.
"""

DISPOSITIONS = {
    "TIMING_UNBILLED": {"treatment": "ROLL_TO_NEXT_BILLING", "requires_approval": False, "authority": "AUTO_INFORMATIONAL"},
    "APPROVED_EXCLUSION": {"treatment": "RESTATE_COMPLIANCE_BASE", "requires_approval": False, "authority": "AUTO_STATUTORY_LOG"},
    "FX_REVALUATION": {"treatment": "LOG_REJECTION", "requires_approval": False, "authority": "LOGGED"},
    "MISCLASSIFICATION": {"treatment": "DRAFT_RECLASS", "requires_approval": True, "authority": "CONTROLLER_REVIEW"},
    "GENUINE_TP_DEVIATION": {"treatment": "DRAFT_TRUE_UP", "requires_approval": True, "authority": "ESCALATE_CONTROLLER_SIGNOFF"},
    "ERP_CUTOVER_ARTIFACT": {"treatment": "WRITE_OFF_TO_PL", "requires_approval": True, "authority": "ESCALATE_ABOVE_WRITEOFF_THRESHOLD"},
    "UNREVERSED_FX_REVALUATION": {"treatment": "DRAFT_REVERSING_JE", "requires_approval": True, "authority": "CONTROLLER_REVIEW"},
    "DUPLICATE_AP_VENDOR_FEED": {"treatment": "DRAFT_REVERSAL_OF_DUPLICATES", "requires_approval": True, "authority": "CONTROLLER_REVIEW"},
    "ACCRUED_MARGIN_PLUG": {"treatment": "REOPEN_FOR_RETRO_INVESTIGATION", "requires_approval": False, "authority": "INFORMATIONAL"},
    "LIVE_COLLECTIBLE_RECEIVABLE": {"treatment": "REINSTATE_AND_COLLECT", "requires_approval": True, "authority": "CONTROLLER_APPROVES_COLLECTION"},
    "UNTRACEABLE": {"treatment": "ESCALATE", "requires_approval": True, "authority": "ESCALATE"},
}


def get_disposition(classification: str) -> dict:
    if classification not in DISPOSITIONS:
        raise ValueError(f"Unknown classification: {classification}")
    return DISPOSITIONS[classification]
