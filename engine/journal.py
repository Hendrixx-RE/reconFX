"""STUB — Phase 2 owner may replace/refine. Builds balanced JE payloads.

Kept minimal: agent/tools.draft_journal_entry already asserts debits equal
credits for whatever lines it is given, so this module just adds a couple
of named constructors used by Act I/II for readability.
"""

from decimal import Decimal


def draft_reclass(amount: Decimal, debit_account: str, credit_account: str, description: str = "") -> dict:
    return {
        "entry_type": "GL_RECLASS",
        "status": "DRAFT",
        "lines": [
            {"account": debit_account, "description": description, "debit": float(amount), "credit": 0.0},
            {"account": credit_account, "description": description, "debit": 0.0, "credit": float(amount)},
        ],
    }
