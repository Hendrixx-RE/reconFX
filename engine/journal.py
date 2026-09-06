"""Journal entry construction (README.md §5.3 engine/journal.py).

Builds balanced JE payloads. Debits must equal credits before a JournalEntry
can be constructed at all — the assertion lives in __post_init__ so it is
impossible to hold an unbalanced entry in memory, not just impossible to
post one.
"""

from dataclasses import dataclass, field
from decimal import Decimal


@dataclass(frozen=True)
class JournalLine:
    account: str
    description: str
    debit: Decimal = Decimal("0")
    credit: Decimal = Decimal("0")
    entity: str = ""


@dataclass(frozen=True)
class JournalEntry:
    entry_type: str
    lines: list[JournalLine]
    supporting_evidence: list[str] = field(default_factory=list)
    requires_approval: bool = True
    status: str = "DRAFT"

    def __post_init__(self):
        total_debit = sum((l.debit for l in self.lines), Decimal("0"))
        total_credit = sum((l.credit for l in self.lines), Decimal("0"))
        if total_debit != total_credit:
            raise ValueError(
                f"Unbalanced journal entry: debits {total_debit} != credits {total_credit}"
            )

    def as_dict(self) -> dict:
        return {
            "entry_type": self.entry_type,
            "status": self.status,
            "requires_approval": self.requires_approval,
            "supporting_evidence": self.supporting_evidence,
            "lines": [
                {
                    "account": l.account,
                    "description": l.description,
                    "debit": str(l.debit),
                    "credit": str(l.credit),
                    "entity": l.entity,
                }
                for l in self.lines
            ],
        }


def draft_reclass(
    amount: Decimal, debit_account: str, credit_account: str, description: str = "", evidence: list[str] | None = None
) -> JournalEntry:
    return JournalEntry(
        entry_type="GL_RECLASS",
        lines=[
            JournalLine(account=debit_account, description=description, debit=amount),
            JournalLine(account=credit_account, description=description, credit=amount),
        ],
        supporting_evidence=evidence or [],
    )


def draft_true_up(
    amount: Decimal,
    provider_entity: str,
    recipient_entity: str,
    evidence: list[str] | None = None,
) -> JournalEntry:
    """Mirrors README.md Appendix C's proposed_journal_entry: a four-line
    intercompany true-up across both entities."""
    return JournalEntry(
        entry_type="TP_TRUE_UP",
        lines=[
            JournalLine(entity=provider_entity, account="1200", description="Intercompany Receivable", debit=amount),
            JournalLine(entity=provider_entity, account="4100", description="Intercompany Service Revenue", credit=amount),
            JournalLine(entity=recipient_entity, account="6300", description="Intercompany Engineering Expense", debit=amount),
            JournalLine(entity=recipient_entity, account="2100", description="Intercompany Payable", credit=amount),
        ],
        supporting_evidence=evidence or [],
    )
