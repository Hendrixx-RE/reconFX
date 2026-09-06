# reconFX — Build Plan

**Syndicate by Maximor · Track 2 (Autonomous Office of the CFO) · 10-hour build**

Hosted by **Agent Orchestrator**, with **Maximor AI**, **Dodo Payments**, **AI Grants India**, **Neatlogs**, and **Tensormux**.

---

## How to use this document

This is an execution spec, not a pitch deck. It is written so that an engineer or a coding agent can open it, start at Phase 1, and build without asking follow-up questions.

Rules for anyone working from this file:

1. **The numbers in Section 4 are canonical.** Do not invent, round, or "improve" them. Every figure in the demo, the UI, and the pitch traces back to that table. If a computed value disagrees with Section 4, the code is wrong, not the table.
2. **Phases are sequential and gated.** Each phase has an exit criterion. Do not start the next phase until the current one passes its acceptance test. A half-finished Phase 3 with a beautiful Phase 5 on top of it loses this hackathon.
3. **Every phase has a "cut list."** If you are running behind at the phase boundary, cut from that list in the order given. Do not improvise cuts.
4. **Anything not in this document is out of scope.** Section 10.3 lists the things that will feel tempting and must not be built.

---

# Section 0 — Project identity

**Name:** reconFX
*(Optional rename to "Strata" or "Bedrock" if there is spare time in Phase 6. It is a string constant. Do not spend build time on it.)*

**One-line pitch:**
> Transfer-pricing systems tell you your margin is off. reconFX reconstructs why, cause by cause, until only the real number is left — then makes sure next month's unexplained amount never gets buried in the first place.

**Two-sentence version for judges:**
> Every finance team has a clearing account holding years of unexplained balance that nobody can trace, because the standard practice when a variance can't be explained is to accrue it away and move on. reconFX excavates that buried balance into dated, evidenced causes, then runs the same decomposition engine forward on the current close so nothing new gets buried.

**Persona:** Corporate Controller / Director of International Tax & Transfer Pricing at a multi-entity company (US parent, India engineering subsidiary).

**Track 2 loop coverage:**

| Required stage | Where it happens in reconFX |
|---|---|
| Detect | Act I detects an unexplained clearing balance. Act II detects a margin breach against TP policy. |
| Investigate | Both acts run the same hypothesis → evidence → quantification loop across GL, payroll, contracts, policy memos, and invoice lines. |
| Decide | Each factor is classified and assigned an accounting disposition (reverse / reclass / roll forward / collect / write off / true-up). |
| Act | Drafts journal entries, drafts an April billing inclusion, and triggers a real collection through Dodo Payments. |
| Escalate | Never auto-posts a genuine transfer-pricing true-up. Halts on insufficient evidence and produces an escalation packet naming exactly which evidence would resolve it. |

---

# Section 1 — Final problem statement

## 1.1 The stated problem

Multinational finance teams run two disconnected processes that both end in the same failure.

**Forward-looking:** Operational transfer-pricing tools (EXA, CCH Tagetik, Hyperbots) monitor whether a legal entity's margin sits inside policy. When it drifts, they compute the true-up required to close the gap and propose posting it. They do not ask why the gap exists. A margin shortfall caused by a payroll run that posted three days after the billing cutoff is treated identically to a genuine mispricing, and gets a permanent tax-relevant adjustment it should never receive. Under OECD BEPS Pillar Two scrutiny, month-end true-ups without transaction-level substantiation are routinely disallowed, producing double taxation and penalties.

**Backward-looking:** Intercompany reconciliation and close tools (BlackLine, Taxilla, HighRadius, Maximor) match transactions and flag imbalances. When a variance resists explanation and corporate policy mandates that intercompany balances net to zero, the controller accrues the difference into a clearing or suspense account to force the balance. That entry is never revisited. Over years, the clearing account accumulates a balance that is treated as permanently unknowable, gets a one-line disclosure, and rolls forward indefinitely.

**These are the same failure at two points in time.** The suspense balance *is* the accumulated residue of every investigation that was abandoned. The reason nobody investigates the balance is that the investigation is expensive; the reason the balance exists is that the investigation was skipped.

## 1.2 What no existing product does

Based on the competitive review already completed (Maximor, EXA, CCH Tagetik, BlackLine, Taxilla, HighRadius, Savant, Hyperbots), the following capabilities are all well covered and **we claim no novelty in any of them**:

- Intercompany transaction matching and elimination
- Margin monitoring and TP breach detection
- True-up calculation and automated posting
- GL anomaly detection and flux analysis
- Automated reclassification entries and dispute workflow

The gap is narrower and specific:

> **No reviewed product performs multi-source forensic causal decomposition — separating timing differences, GL misclassifications, and approved policy exclusions from genuine transfer-pricing deviations — before a true-up is posted; and no reviewed product runs that decomposition retrospectively across an accumulated unexplained balance.**

The reason is structural. Existing tools reason over structured ledger tables. The evidence needed to explain a variance lives in payroll posting timestamps, contract clauses, billing-run configuration, and approval memos written in prose. Rule engines cannot join those. An agent with tools can.

## 1.3 What we claim, precisely

One claim, stated so it survives adversarial questioning:

> Decomposing an unexplained financial balance — whether a current-period margin deviation or a multi-year accumulated suspense balance — into named, dated, evidence-backed causal factors under a strict non-overlap constraint, reducing it to a true residual with a stated disposition per factor and an honest escalation for what remains unexplained.

Not detection. Not matching. Not the true-up arithmetic. The decomposition.

## 1.4 Why the two acts belong in one product

Three reasons, in order of strength:

1. **Causal, not thematic.** The buried balance is literally made of skipped investigations. Act I finds $290,000 of accrued margin plugs inside the clearing account — eleven months of precisely the investigation Act II performs. Act II justifies itself with evidence produced by Act I.
2. **One engine, two entry points.** Identical decomposition math, identical exclusivity constraint, identical residual tracker, identical evidence model, identical escalation matrix. The only difference is the time range of the query and the disposition vocabulary.
3. **The excavation trains the investigation.** Act I produces a failure profile for the entity — which causes actually recur here. Act II reads that profile and orders its hypotheses by it. This is Maximor's own stated philosophy (Learn → Run → Escalate → Improve) executed rather than name-checked, in front of judges hosted by Maximor.

---

# Section 2 — The solution, stage by stage

## 2.1 System summary

reconFX is a hybrid agent: a **deterministic Python financial engine** that owns all arithmetic and set logic, and an **LLM cognitive layer** that owns hypothesis generation, unstructured evidence interpretation, document precedence, and memo drafting. The LLM never computes a dollar amount. The engine never decides what a document means. This split is what makes the output audit-defensible and eliminates arithmetic hallucination.

```
┌────────────────────────────────────────────────────────────┐
│  Controller Console (React)                                 │
│  Left: agent trace stream  │  Right: decomposition view     │
└──────────────┬─────────────────────────────────────────────┘
               │ WebSocket (state events)
┌──────────────▼─────────────────────────────────────────────┐
│  Orchestrator (FastAPI + Python)                            │
│                                                             │
│  ┌──────────────────┐        ┌───────────────────────────┐ │
│  │ LLM Cognitive    │        │ Deterministic Engine      │ │
│  │ Layer            │───────▶│ • baseline math           │ │
│  │ • hypothesise    │        │ • exclusivity enforcement │ │
│  │ • read prose     │◀───────│ • factor quantification   │ │
│  │ • precedence     │        │ • residual tracker        │ │
│  │ • draft memos    │        │ • materiality gate        │ │
│  └──────────────────┘        └───────────────────────────┘ │
│         │  via Tensormux            │                       │
│         │                           │                       │
│  ┌──────▼───────────────────────────▼──────────────────┐   │
│  │ Tool layer (7 tools, all Neatlogs-instrumented)     │   │
│  └──────┬───────────────────────────────────────────────┘   │
└─────────┼───────────────────────────────────────────────────┘
          │
   ┌──────▼──────┐   ┌──────────────┐   ┌──────────────────┐
   │ Evidence    │   │ AO Lua       │   │ Dodo Payments    │
   │ corpus      │   │ process      │   │ (collection)     │
   │ (8 files)   │   │ (audit ledger)│  │                  │
   └─────────────┘   └──────────────┘   └──────────────────┘
```

## 2.2 Act I — The excavation (retrospective)

**Trigger:** Controller points the agent at GL account **1900 – Intercompany Clearing**, balance **$1,847,000**, oldest open item 38 months old, owner unassigned.

**Stage 1 — Detect.** `query_clearing_account()` pulls all open items in 1900 across 38 months. The engine computes total balance, item count, age distribution, and flags that no item carries a clearing reference.

**Stage 2 — Stratify.** The LLM layer receives the item metadata (dates, source systems, descriptions, amounts, counterparties) and proposes candidate strata — clusters of items likely to share a single root cause. It proposes, it does not confirm. Each proposal states the pattern it thinks it sees and the evidence that would confirm it.

**Stage 3 — Confirm each stratum with evidence.** For each candidate, the agent calls the tool that would prove or kill it:

| Candidate stratum | Confirming evidence | Tool |
|---|---|---|
| ERP cutover artifacts | `source_system = LEGACY_MIGRATION`, cluster within the migration window in `migration_log.json` | `query_clearing_account`, `get_policy` |
| Unreversed FX revaluation | Revaluation entries with no matching reversal in the following period | `query_clearing_account` |
| Duplicate AP vendor feed | Identical vendor + amount + vendor invoice ref, distinct doc IDs, same day | `query_gl` |
| Accrued margin plugs | Description pattern + monthly cadence + amounts matching prior margin variances | `query_clearing_account` |
| Live collectible receivable | Customer contract still active, invoicing stopped mid-term | `get_policy`, `query_gl` |
| Untraceable | No trail found after all tools exhausted | — |

**Stage 4 — Quantify deterministically.** Each confirmed stratum passes its transaction ID set to `test_hypothesis()`. The engine asserts the sets are disjoint, sums the line amounts, and decrements the running unexplained balance.

**Stage 5 — Assign disposition.** Each stratum gets an accounting treatment and an authority level. Reversals and collections are draftable; write-offs above materiality require sign-off; the untraceable remainder escalates.

**Stage 6 — Emit the cause profile.** The agent counts the margin-plug stratum by month and correlates each plug month against the GL pattern in that month, producing a ranked prior over cause categories for this entity. Written to `cause_profile.json` and committed to the AO ledger.

**Act I output:** $1,847,000 decomposed into six named strata, $92,000 honestly escalated as untraceable, $263,000 identified as live recoverable cash, and a cause profile that Act II consumes.

## 2.3 The bridge

The console shows one line before Act II begins:

> *Of the $1,847,000 buried in this account, $290,000 across 11 months was accrued to close margin variances nobody investigated. In 7 of those 11 months, payroll posted after the billing cutoff. Prior for this entity: timing 64%.*

Then: *This month's variance is about to become the twelfth.*

## 2.4 Act II — The live investigation (prospective)

**Trigger:** March 2026 close. TP monitor reports ENT-IN-02 effective markup **8.41%** against a **10.00%** policy target. Deviation **$44,000**. Standard behaviour would be to post a $44,000 true-up or accrue it to account 1900.

**Stage 1 — Establish baseline.** `get_policy()` returns markup target, eligible cost centres, eligible and excluded GL accounts, billing cutoff day, and materiality threshold. The engine computes the naive eligible cost base, target markup profit, recognised markup profit, and the opening deviation. All four are recomputed from source, never trusted from the alert.

**Stage 2 — Order hypotheses using the Act I prior.** The LLM generates candidate hypotheses and ranks them by the cause profile. The console displays the prior driving the ordering. This is visible, not implicit.

**Stage 3 — Test each hypothesis.**

- **H1 Timing.** `query_payroll()` finds a $310,000 off-cycle run with a March service period posted on 03-28. `get_policy()` gives cutoff day 25. `query_gl()` confirms the cost is in an eligible account. The invoice line file confirms it was not billed. Factor: **$31,000**. Residual $44,000 → **$13,000**.
- **H2 Approved exclusion.** `query_gl()` shows $80,000 of severance posted to eligible account 6120 in eligible cost centre CC-102 — so the margin monitor counted it in the base — but the invoice line file shows the billing engine excluded it. Two systems disagree. `query_approvals()` finds memo **EXP-2026-08**, a permanent exclusion of restructuring costs approved by the VP of Corporate Tax. Document precedence resolves it: the exception memo outranks the GL account mapping. The billing engine was right, the monitor's base was wrong. Factor: **$8,000**. Residual $13,000 → **$5,000**.
- **H3 FX revaluation.** The agent tests whether FX revaluation on intercompany balances explains the remainder. `query_gl()` returns net movement on account 7700 of **$340**, below the $500 materiality threshold. **Hypothesis rejected and logged.** Residual unchanged at $5,000.
- **H4 Misclassification (separate axis).** `query_gl()` finds $140,000 of DevOps SaaS licences posted to excluded account 6800 under eligible cost centre CC-100. The description proves the cost is rechargeable engineering software belonging in 6100. Because 6800 is excluded, this cost is invisible to both the margin monitor and the billing engine — it is not part of the deviation. Correcting it **increases** the entity's entitlement by **$14,000** that was never billed. This is recorded as a recovery finding, not a residual reduction.

**Stage 4 — Decide dispositions.**

| Finding | Treatment | True-up? | Authority |
|---|---|---|---|
| $31,000 timing | Roll $310,000 into the April intercompany billing run | No | Auto — informational log |
| $8,000 exclusion | Restate compliance base to exclude $80,000; margin on eligible base is compliant | No | Auto — statutory audit log |
| $340 FX | Rejected below materiality | No | Logged rejection |
| $14,000 recovery | Draft GL reclass Dr 6100 / Cr 6800 $140,000; add to April billing | No | Draft — controller review |
| $5,000 residual | Genuine TP deviation. Effective rate applied was 9.79% against a 10.00% contract. Billing-engine configuration log not available, so the cause is stated as probable, not proven. | **Yes** | **Escalate — controller sign-off required** |

**Stage 5 — Escalate.** The agent halts. It produces an escalation packet containing the draft true-up JE, the full evidence chain per factor, the rejected hypothesis, and an explicit statement of what evidence would close the residual (the March billing-run configuration export). The controller approves or rejects in the console.

**Act II output:** A $44,000 deviation reduced to a $5,000 substantiated true-up, $14,000 of recovered entitlement, and zero dollars accrued to account 1900.

## 2.5 The closing frame

> Last month, $44,000 would have gone into account 1900 and joined the $290,000 already there. This month, $5,000 goes to a controller with an evidence packet, and $39,000 goes back to where it belongs.

---

# Section 3 — The deterministic model

All of this lives in Python. The LLM has no access to these functions except through `test_hypothesis()`, and receives only their outputs.

## 3.1 Act II baseline

Let:

- `m_target` = contractual markup rate (0.10)
- `E_naive` = cost base as computed by a standard OTP monitor: all GL lines where `gl_account ∈ eligible_gl_accounts` AND `cost_center ∈ eligible_cost_centers`
- `B` = cost base actually billed, taken from `intercompany_invoice_lines.csv`
- `R` = intercompany revenue actually recorded

```
target_profit     = m_target × E_naive
recognised_profit = R − B
Δ₀                = target_profit − recognised_profit
effective_markup  = recognised_profit / E_naive
```

## 3.2 Decomposition

Δ₀ decomposes into `n` factors plus a residual:

```
Δ₀ = Σᵢ₌₁ⁿ Fᵢ + ρ
```

Residual after each validated factor:

```
ρₖ = Δ₀ − Σᵢ₌₁ᵏ Fᵢ
```

## 3.3 Non-overlap constraint (the audit guarantee)

Let `T` be the set of all GL line items in scope. Each factor `Fᵢ` maps to a subset `Tᵢ ⊆ T`.

```
Tᵢ ∩ Tⱼ = ∅   for all i ≠ j
```

`test_hypothesis()` **rejects any factor whose transaction set intersects an already-accepted set**, and returns the offending doc IDs. This is the single most important line of code in the project. It is what makes double-counting structurally impossible rather than merely unlikely, and it is the correct answer when a judge asks how you prevent the agent from over-explaining.

## 3.4 Factor quantification

```
Fᵢ = αᵢ × Σ_{t ∈ Tᵢ} amount(t)
```

where `αᵢ` is set by classification, never by the model:

| Classification | α | Rationale |
|---|---|---|
| `TIMING_UNBILLED` | `m_target` | Only the markup was foregone; the cost rolls to next period |
| `MISCLASSIFICATION` | `m_target` | Only the markup was foregone; cost was correctly incurred |
| `APPROVED_EXCLUSION` | `m_target` | Removes the cost from the base, removing its markup from target |
| `FX_REVALUATION` | `1.0` | Revenue-side error, full dollar impact |
| `GENUINE_TP_DEVIATION` | `1.0` | Full profit shortfall |

## 3.5 Materiality gate

```
if abs(Fᵢ) < materiality_threshold:
    reject_hypothesis(Fᵢ, reason="below_materiality")
```

Rejections are logged and displayed. A rejected hypothesis is evidence of judgment, not a failure.

## 3.6 Termination

```
if abs(ρₖ) < materiality_threshold:   → FULLY_EXPLAINED, terminate
elif hypotheses_exhausted:            → ESCALATE with residual and required-evidence list
elif step_count > MAX_STEPS (12):     → ESCALATE (loop guard)
```

## 3.7 Act I variant

Identical structure. `Δ₀` is the clearing account balance, `α = 1.0` for every stratum (all impacts are full dollar amounts), and the exclusivity constraint runs over clearing-account line IDs. Dispositions differ; the math does not.

---

# Section 4 — Canonical dataset

**These numbers are frozen.** Build a test in Phase 1 that asserts them and run it at the end of every phase.

## 4.1 Act II — March 2026, ENT-IN-02 → ENT-US-01

### `entity_gl.csv`

```csv
doc_id,posting_date,cost_center,gl_account,account_description,amount_usd,description,source_system,vendor_invoice_ref
GL-2026-0301,2026-03-05,CC-100,6100,Direct Engineering Payroll,1700000.00,March Engineering Base Payroll,PAYROLL,
GL-2026-0302,2026-03-10,CC-101,6110,Cloud Infrastructure,420000.00,AWS Production Hosting Charges,AP_INVOICE,AWS-MAR-2026
GL-2026-0303,2026-03-14,CC-102,6120,Professional & Contractor Fees,160000.00,Engineering Contractor Fees,AP_INVOICE,CTR-2026-0311
GL-2026-0304,2026-03-18,CC-100,6200,Engineering Tooling,90000.00,Test Hardware and Lab Equipment,AP_INVOICE,TOOL-2026-04
GL-2026-0305,2026-03-22,CC-100,6800,Local Admin Overhead,140000.00,DevOps SaaS Software Licenses - Engineering,AP_INVOICE,SAAS-2026-Q1
GL-2026-0306,2026-03-24,CC-102,6120,Professional & Contractor Fees,80000.00,Executive Severance Settlement,AP_INVOICE,SEV-2026-02
GL-2026-0307,2026-03-28,CC-100,6100,Direct Engineering Payroll,310000.00,Off-Cycle Late Engineering Payroll,PAYROLL,
GL-2026-0308,2026-03-31,CC-100,7100,Local Facilities,96000.00,Bengaluru Office Facilities and Utilities,AP_INVOICE,FAC-2026-03
GL-2026-0309,2026-03-31,CC-100,7700,FX Revaluation,340.00,FX Revaluation - Intercompany Balances,GL_ADJ,
```

### `tp_policy.json`

```json
{
  "policy_id": "TP-POL-2026-ENG",
  "policy_name": "Global Engineering Cost-Plus Services Agreement",
  "effective_date": "2026-01-01",
  "expiry_date": "2026-12-31",
  "method": "COST_PLUS_TNMM",
  "target_markup_percent": 10.0,
  "billing_cutoff_day_of_month": 25,
  "eligible_cost_centers": ["CC-100", "CC-101", "CC-102"],
  "eligible_gl_accounts": ["6100", "6110", "6120", "6200"],
  "excluded_gl_accounts": ["6800", "6900", "7100", "7700"],
  "materiality_threshold_usd": 500.0,
  "document_precedence": [
    "APPROVED_POLICY_EXCEPTION_MEMO",
    "INTERCOMPANY_CONTRACT",
    "TP_POLICY_GL_MAPPING",
    "GL_LINE_DESCRIPTION"
  ]
}
```

### `intercompany_contract.json`

```json
{
  "contract_id": "ICC-US-IN-001",
  "provider_entity": "ENT-IN-02",
  "provider_name": "Maximor India Engineering Pvt Ltd",
  "recipient_entity": "ENT-US-01",
  "recipient_name": "Maximor Inc USA",
  "billing_currency": "USD",
  "local_currency": "INR",
  "fx_rate_agreed": 83.50,
  "fx_rate_basis": "CONTRACTUAL_FIXED",
  "payment_terms": "NET_30",
  "clearing_account": "1900"
}
```

### `payroll_register.csv`

```csv
payroll_id,employee_group,cost_center,service_period_start,service_period_end,posting_date,gross_pay_usd,pay_type
PAY-2026-M1,ENG-FULLTIME,CC-100,2026-03-01,2026-03-25,2026-03-05,1700000.00,REGULAR
PAY-2026-M2,ENG-CONTRACT,CC-100,2026-03-01,2026-03-25,2026-03-28,310000.00,OFF_CYCLE_LATE
```

Note that PAY-2026-M2 has a **March service period** but an **03-28 posting date**. That is the entire timing finding: the work was performed in the billed period, the cost landed after the cutoff.

### `policy_exceptions.json`

```json
[
  {
    "exception_id": "EXP-2026-08",
    "entity_id": "ENT-IN-02",
    "applies_to_gl_accounts": ["6120", "6900"],
    "approved_amount_usd": 80000.00,
    "effective_period": "2026-03",
    "approval_type": "PERMANENT_EXCLUSION",
    "approver": "VP Corporate Tax",
    "approval_date": "2026-03-19",
    "reason_code": "RESTRUCTURING_SEVERANCE",
    "narrative": "Executive severance settlement arising from the March 2026 leadership restructuring is excluded from the cost-plus service fee base for the duration of the 2026 agreement. This exclusion is permanent and is not to be recovered through any subsequent true-up.",
    "documentation_link": "doc_store/EXP-2026-08_memo.pdf"
  }
]
```

### `intercompany_invoices.csv`

```csv
invoice_id,invoice_date,provider_entity,recipient_entity,billed_cost_base_usd,markup_applied_percent,total_billed_usd,fx_rate_applied
INV-IC-2026-03,2026-03-25,ENT-IN-02,ENT-US-01,2370000.00,9.79,2602000.00,83.50
```

### `intercompany_invoice_lines.csv`

```csv
invoice_id,line_no,gl_doc_id,billed_amount_usd,recharge_flag,exclusion_reason
INV-IC-2026-03,1,GL-2026-0301,1700000.00,Y,
INV-IC-2026-03,2,GL-2026-0302,420000.00,Y,
INV-IC-2026-03,3,GL-2026-0303,160000.00,Y,
INV-IC-2026-03,4,GL-2026-0304,90000.00,Y,
INV-IC-2026-03,5,GL-2026-0306,0.00,N,LOCAL_AP_BLOCK_NO_REASON_CODED
```

This file is what creates the two-system disagreement in H2. The billing engine blocked the severance with no reason code; the margin monitor counted it. Only the approval memo resolves who was right.

### Verified Act II arithmetic

| Quantity | Value | Derivation |
|---|---|---|
| `E_naive` | **$2,760,000** | 1,700,000 + 420,000 + 160,000 + 90,000 + 80,000 + 310,000 |
| `target_profit` | **$276,000** | 10% × 2,760,000 |
| `B` | **$2,370,000** | Invoice lines with `recharge_flag = Y` |
| `R` | **$2,602,000** | Recorded intercompany revenue |
| `recognised_profit` | **$232,000** | 2,602,000 − 2,370,000 |
| `effective_markup` | **8.41%** | 232,000 / 2,760,000 |
| **Δ₀** | **$44,000** | 276,000 − 232,000 |
| F1 timing | **$31,000** | 10% × 310,000 → ρ = $13,000 |
| F2 approved exclusion | **$8,000** | 10% × 80,000 → ρ = $5,000 |
| H3 FX | **$340 — rejected** | Below $500 materiality → ρ = $5,000 |
| **Residual** | **$5,000** | Effective rate applied 9.79% vs contractual 10.00% on $2,370,000 |
| Recovery (separate axis) | **+$14,000** | 10% × 140,000 misclassified to excluded 6800 |

Reconciliation check: `31,000 + 8,000 + 5,000 = 44,000` ✅

## 4.2 Act I — Clearing account 1900

`clearing_ledger.csv` contains roughly 55 line items spanning 2023-02 to 2026-02. Total open balance **$1,847,000**.

| # | Stratum | Amount | Items | Detection signature | Disposition | Authority |
|---|---|---|---|---|---|---|
| 1 | ERP cutover artifacts | $612,000 | 9 | `source_system = LEGACY_MIGRATION`, all posted 2023-04-01 to 2023-04-05, matching the window in `migration_log.json` | Write off to P&L | Escalate — above write-off threshold |
| 2 | Unreversed FX revaluation | $384,000 | 6 | `description` contains `FX REVAL`, no reversal entry in the following period | Draft reversing JE | Draft — controller review |
| 3 | Duplicate AP vendor feed | $206,000 | 14 | Identical `vendor_invoice_ref` + amount + date, distinct doc IDs, all 2024-03-11 | Draft reversal of 14 duplicates | Draft — controller review |
| 4 | Accrued IC margin plugs | $290,000 | 11 | `description` matches `IC margin plug`, monthly cadence 2024-06 to 2025-04 | Re-open for retro-investigation; seeds the cause profile | Informational |
| 5 | Live collectible receivable | $263,000 | 3 | Customer `CUST-4471`, invoicing ceased 2024-08, contract active through 2026-12 | **Reinstate and collect via Dodo Payments** | Draft — controller approves collection |
| 6 | Untraceable | $92,000 | 12 | No corroborating record found across all tools | **Escalate** with required-evidence list | Escalate |

Total: `612,000 + 384,000 + 206,000 + 290,000 + 263,000 + 92,000 = 1,847,000` ✅

The $92,000 is not a defect. An agent that explains 100% of a three-year suspense balance is lying, and any controller in the room knows it. Surfacing the unexplainable with a specific list of what would resolve it is the honest behaviour the "human judgment" criterion is asking for.

## 4.3 `cause_profile.json` — the bridge artifact

Produced by Act I, consumed by Act II.

```json
{
  "entity_id": "ENT-IN-02",
  "derived_from": "clearing_account_1900_excavation",
  "plug_months_analysed": 11,
  "period_range": "2024-06 to 2025-04",
  "cause_priors": [
    { "cause": "TIMING_UNBILLED",     "occurrences": 7, "prior": 0.64,
      "signature": "eligible-account cost posted after billing_cutoff_day_of_month" },
    { "cause": "MISCLASSIFICATION",   "occurrences": 2, "prior": 0.18,
      "signature": "rechargeable description in excluded GL account" },
    { "cause": "APPROVED_EXCLUSION",  "occurrences": 1, "prior": 0.09,
      "signature": "policy exception memo not tagged in ERP" },
    { "cause": "UNRESOLVED",          "occurrences": 1, "prior": 0.09,
      "signature": "no evidence trail located" }
  ],
  "recommended_hypothesis_order": [
    "TIMING_UNBILLED", "MISCLASSIFICATION", "APPROVED_EXCLUSION", "FX_REVALUATION"
  ]
}
```

## 4.4 Supporting files

- `migration_log.json` — NetSuite cutover window, 2023-04-01 to 2023-04-05, with the batch IDs that appear in the clearing ledger.
- `customer_contracts.json` — `CUST-4471` contract, active through 2026-12, monthly value, last invoice date 2024-08.
- `doc_store/EXP-2026-08_memo.pdf` — one-page approval memo. Generate with `reportlab`. The narrative text must match `policy_exceptions.json` so the agent can cross-verify.

---

# Section 5 — Architecture and stack

## 5.1 Components

| Layer | Technology | Responsibility |
|---|---|---|
| Deterministic engine | Python 3.11, pandas | All arithmetic, set operations, exclusivity enforcement, residual tracking, materiality gating |
| Agent runtime | Python, custom ReAct loop (**do not use a framework**) | Hypothesis generation, tool dispatch, step limiting, state machine |
| Model access | **Tensormux** gateway | Routes bulk classification to a fast model, policy reasoning and memo drafting to a strong model |
| Observability | **Neatlogs** | Spans on every tool call, LLM turn, hypothesis acceptance and rejection |
| Audit ledger | **Agent Orchestrator** (aos Lua process) | Immutable, append-only record of every decomposition step and controller decision |
| Payment action | **Dodo Payments** | Collection of the $263,000 recovered receivable |
| API | FastAPI + WebSocket | Streams state events to the console |
| Console | React + Vite + Recharts | Two-act controller interface |

**Why no agent framework.** LangGraph or CrewAI adds an orchestration layer you will spend two hours debugging under time pressure, and it obscures the reasoning trail judges want to inspect. A ~150-line ReAct loop with an explicit step counter and a hard cap is more reliable, more legible, and faster to write. Neatlogs instruments raw functions perfectly well.

## 5.2 Tool interface

Seven tools. Every one is `@neatlogs.span(kind="TOOL")` decorated and returns a JSON-serialisable dict with an `evidence_refs` list.

```python
get_policy(entity_id: str, period: str) -> dict
    """TP policy, contract terms, GL mappings, precedence order, materiality."""

query_gl(entity_id: str, period_start: str, period_end: str,
         gl_accounts: list[str] | None = None,
         cost_centers: list[str] | None = None,
         description_contains: str | None = None) -> list[dict]
    """GL line items. Supports the descriptive filters the LLM needs to test
       misclassification and duplicate hypotheses."""

query_payroll(entity_id: str, period: str) -> list[dict]
    """Payroll runs with service period AND posting date. The gap between
       the two is the timing finding."""

query_approvals(entity_id: str, period: str,
                gl_account: str | None = None) -> list[dict]
    """Policy exception memos, including narrative text and doc links."""

query_clearing_account(account: str, from_date: str, to_date: str) -> list[dict]
    """Act I. Open items in the clearing account across the full history."""

test_hypothesis(cause_id: str, classification: str,
                transaction_ids: list[str],
                evidence_refs: list[str]) -> dict
    """THE GATE. Validates exclusivity against accepted sets, applies α by
       classification, computes the factor deterministically, applies the
       materiality gate, updates the residual, emits an AO message.
       Returns {accepted, factor_usd, new_residual, rejection_reason}."""

draft_journal_entry(entry_type: str, lines: list[dict],
                    supporting_evidence: list[str],
                    requires_approval: bool) -> dict
    """Structured JE payload. Never posts. Status is always DRAFT."""

escalate(reason: str, residual_usd: float,
         evidence_gap: list[str], packet: dict) -> dict
    """Halts execution. Emits the controller packet with an explicit list of
       what evidence would close the gap."""
```

**Contract:** the LLM may never return a dollar figure that ends up in the ledger. It returns `transaction_ids` and a `classification`. `test_hypothesis()` computes the money. If a value in the UI did not come from the engine, it is a bug.

## 5.3 Repository layout

```
reconfx/
├── PLAN.md
├── .env.example
├── requirements.txt
├── data/
│   ├── tp_policy.json
│   ├── intercompany_contract.json
│   ├── entity_gl.csv
│   ├── payroll_register.csv
│   ├── policy_exceptions.json
│   ├── intercompany_invoices.csv
│   ├── intercompany_invoice_lines.csv
│   ├── clearing_ledger.csv
│   ├── migration_log.json
│   ├── customer_contracts.json
│   ├── cause_profile.json          # written by Act I
│   └── doc_store/
│       └── EXP-2026-08_memo.pdf
├── engine/
│   ├── __init__.py
│   ├── baseline.py                 # §3.1
│   ├── decomposition.py            # §3.2–3.5 exclusivity, α, residual
│   ├── dispositions.py             # treatment + authority routing
│   └── journal.py                  # JE construction
├── agent/
│   ├── loop.py                     # ReAct loop, step cap
│   ├── tools.py                    # §5.2, Neatlogs-instrumented
│   ├── prompts.py                  # system + hypothesis prompts
│   ├── act_one.py                  # excavation orchestration
│   ├── act_two.py                  # live investigation orchestration
│   └── model.py                    # Tensormux client + routing
├── integrations/
│   ├── ao_client.py                # AO message dispatch
│   ├── neatlogs_setup.py
│   └── dodo_client.py
├── ao/
│   └── reconfx_ledger.lua
├── api/
│   ├── main.py                     # FastAPI + WebSocket
│   └── events.py                   # event schema
├── ui/
│   └── src/
│       ├── App.jsx
│       ├── components/
│       │   ├── TraceStream.jsx
│       │   ├── StrataColumn.jsx    # Act I
│       │   ├── ResidualWaterfall.jsx # Act II
│       │   ├── EvidenceCard.jsx
│       │   ├── ApprovalModal.jsx
│       │   └── CostMeter.jsx       # Tensormux cost display
│       └── styles/
└── tests/
    ├── test_canonical_numbers.py   # asserts every figure in §4
    ├── test_exclusivity.py
    └── test_attacks.py             # §10.2 scenarios
```

## 5.4 Environment

```bash
TENSORMUX_API_KEY=
TENSORMUX_BASE_URL=
NEATLOGS_API_KEY=
AO_PROCESS_ID=
AO_WALLET_PATH=./wallet.json
DODO_API_KEY=
DODO_ENV=test
```

---

# Section 6 — Sponsor integration

The hackathon expects the sponsor stack to be used. Each entry below states what it does, why it is the right fit, and — most importantly — **what a judge sees on screen that proves it was used**. Decorative integrations are worse than none; a judge who spots one discounts the rest.

The sponsor integrations are split across two parallel execution tracks:
- **Track A (Ledger, backend & API):** §6.1 Agent Orchestrator, §6.4 Neatlogs
- **Track B (Payments, cost, console experience & delivery):** §6.3 Dodo Payments, §6.5 Tensormux cost meter, §6.6 AI Grants voice (optional)
- **Shared Philosophy / Positioning:** §6.2 Maximor AI (conceptual alignment across both tracks)

---

## Track A — Ledger, backend & API

### 6.1 Agent Orchestrator — mandatory, load-bearing

**Role:** the immutable audit ledger. Not a wrapper, not a mention.

Every accepted factor, every rejected hypothesis, every disposition, and every controller decision is written as a message to a Lua process on aos. Because the ledger is append-only and externally verifiable, the agent's own record cannot be retroactively edited — which is precisely the property a tax authority demands of transfer-pricing substantiation under BEPS Pillar Two. AO is not bolted on; it is the answer to "how do we know the agent didn't rewrite its own reasoning after the fact."

```lua
-- ao/reconfx_ledger.lua
Steps = Steps or {}
Residual = Residual or 0
Decisions = Decisions or {}

Handlers.add("RecordStep",
  Handlers.utils.hasMatchingTag("Action", "RecordStep"),
  function(msg)
    local d = json.decode(msg.Data)
    table.insert(Steps, {
      act            = d.act,                -- "EXCAVATION" | "INVESTIGATION"
      factor_id      = d.factor_id,
      classification = d.classification,
      transaction_ids= d.transaction_ids,
      evidence_refs  = d.evidence_refs,
      factor_usd     = d.factor_usd,
      residual_before= Residual,
      residual_after = d.new_residual,
      accepted       = d.accepted,
      rejection_reason = d.rejection_reason,
      ts             = msg.Timestamp
    })
    Residual = d.new_residual
    ao.send({ Target = msg.From, Data = json.encode({ ok = true, step = #Steps }) })
  end)

Handlers.add("RecordDecision",
  Handlers.utils.hasMatchingTag("Action", "RecordDecision"),
  function(msg)
    local d = json.decode(msg.Data)
    table.insert(Decisions, {
      decision_type = d.decision_type,       -- APPROVE_TRUEUP | APPROVE_COLLECTION | REJECT
      actor         = d.actor,
      payload_hash  = d.payload_hash,
      ts            = msg.Timestamp
    })
    ao.send({ Target = msg.From, Data = json.encode({ ok = true }) })
  end)

Handlers.add("GetLedger",
  Handlers.utils.hasMatchingTag("Action", "GetLedger"),
  function(msg)
    ao.send({ Target = msg.From,
              Data = json.encode({ steps = Steps, decisions = Decisions,
                                   residual = Residual }) })
  end)
```

**Proof on screen:** the console header shows the live AO process ID. Every factor row shows its AO message ID. At the end of the demo, run `Send({Target=PROCESS, Tags={Action="GetLedger"}})` in the aos terminal on camera and show the full step list returned from chain state, not from the app.

**Reliability:** run a local `aos` instance during recording. Wrap `ao_client` calls in a non-blocking queue so network latency cannot stall the agent loop.

### 6.4 Neatlogs — the reasoning is inspectable

**Role:** full execution tracing. Every tool call, model turn, latency figure, hypothesis acceptance and **rejection** is a span.

The rejected FX hypothesis is the span that matters. It is the difference between an agent that reasons and a script that executes, and it is the thing a judge can verify independently by opening the trace.

```python
import neatlogs

neatlogs.init(
    api_key=os.environ["NEATLOGS_API_KEY"],
    workflow_name="reconfx-two-act-decomposition",
)

@neatlogs.span(kind="TOOL")
def query_payroll(entity_id: str, period: str): ...

@neatlogs.span(kind="REASONING")
def generate_hypotheses(context: dict, prior: dict): ...

@neatlogs.span(kind="DECISION")
def test_hypothesis(...): ...
```

**Proof on screen:** a live Neatlogs trace link in the console header. Open it during the demo and scroll to the rejected-hypothesis span. Wrap all Neatlogs calls in `try/except` so a rate limit cannot break the run.

---

## Track B — Payments, cost, console experience & delivery

### 6.3 Dodo Payments — a real payment, not a ceremony

**Role:** collection of the $263,000 receivable recovered in Act I.

Note the deliberate choice. Routing an *intercompany true-up* through a payment rail is decorative — intercompany balances settle through treasury, not a payment gateway, and an accountant on the panel will notice. What Act I surfaces instead is a **live, external, collectible customer receivable** that stopped being invoiced in August 2024. Reinstating and collecting that is a genuine payment action.

Flow: controller reviews stratum 5 → approves collection → `dodo_client.create_payment_link()` creates a hosted invoice for `CUST-4471` → the link is shown in the console → the AO ledger records `APPROVE_COLLECTION` with the Dodo reference.

**Proof on screen:** a real Dodo test-mode payment link, opened in a second browser tab during the demo.

### 6.5 Tensormux — routing with a visible number

**Role:** model gateway with cost-aware routing.

| Workload | Route to | Why |
|---|---|---|
| Bulk classification of ~55 clearing-ledger lines and 9 GL lines | Fast, cheap model | High volume, low judgment |
| Policy interpretation, document precedence, memo narrative reading, JE narration | Strong model | Requires reasoning over prose and conflicting sources |

**Proof on screen:** a cost meter in the console footer showing calls per route and total cost for the investigation, e.g. `Fast: 6 calls · Strong: 4 calls · $0.--`. Then the comparison line: a controller doing this manually costs 4–8 hours. That single number does more competitive work than a slide.

### 6.6 AI Grants India — the escalation gets a voice

**Role:** voice credits, used for the one moment where voice is genuinely better than text.

When the agent escalates the $5,000 residual, it generates a spoken 20-second controller briefing: what was found, what was explained, what remains, what evidence would close it. A controller reviewing escalations on a phone during close week listens rather than reads.

Keep this strictly optional. It is the **first thing cut** if Phase 4 runs long, and its absence costs nothing.

---

## Shared Product Alignment

### 6.2 Maximor AI — the philosophy, executed

**Role:** reconFX is positioned as a specialist forensic layer that sits beside Maximor's close automation, not against it. Maximor's flux analysis explains variance at financial-statement line level; reconFX explains it at operational-event level and hands back structured JE payloads Maximor could ingest.

Make the alignment explicit and visible in the UI, mapped to Maximor's own **Learn → Run → Escalate → Improve**:

| Maximor stage | reconFX implementation |
|---|---|
| **Learn** | Act I excavates 38 months and derives the entity's cause profile |
| **Run** | Act II runs the live close investigation using that profile |
| **Escalate** | The $5,000 residual halts and routes to the controller with an evidence gap statement |
| **Improve** | The controller's decision writes back to `cause_profile.json` and the AO ledger, updating priors for April |

**Proof on screen:** label the four console stages with those words. When the controller approves, show the prior update: `TIMING_UNBILLED 0.64 → 0.67`. That is a closed learning loop, demonstrated in three seconds.

---

# Section 7 — The six phases

Total budget: **10 hours.** Each phase lists objective, inputs, deliverables, acceptance test, exit criterion, and cut list.

---

## PHASE 1 — Foundation and evidence corpus
**Hours 0:00 – 1:15**

### Objective
Produce the complete, frozen, internally consistent evidence corpus and the test that proves it. Nothing downstream can be trusted if this is wrong, and a dataset error discovered at hour 8 is fatal.

### Deliverables

1. All ten data files exactly as specified in Section 4, written into `data/`.
2. `clearing_ledger.csv` — ~55 rows across 38 months. Construct stratum by stratum:
   - 9 rows tagged `LEGACY_MIGRATION`, dated 2023-04-01 to 2023-04-05, summing to $612,000
   - 6 rows with `FX REVAL` in the description, no reversal partner, summing to $384,000
   - 14 rows sharing `vendor_invoice_ref = VND-2024-0311`, identical amounts, distinct doc IDs, all dated 2024-03-11, summing to $206,000
   - 11 rows, one per month 2024-06 through 2025-04, description `IC margin plug - unexplained variance`, summing to $290,000. **Seven of these must fall in months where a post-cutoff payroll posting also exists** — add corresponding stub rows to `payroll_register.csv` so the correlation is real and derivable, not asserted.
   - 3 rows referencing `CUST-4471`, summing to $263,000
   - 12 rows with generic descriptions and no cross-referencable identifier, summing to $92,000
3. `doc_store/EXP-2026-08_memo.pdf` — one page, generated with `reportlab`. Header, approver, date, and the narrative text from `policy_exceptions.json` verbatim.
4. `tests/test_canonical_numbers.py`.

### Acceptance test

```python
def test_act_two_baseline():
    b = compute_baseline("ENT-IN-02", "2026-03")
    assert b.eligible_base       == 2_760_000
    assert b.target_profit       ==   276_000
    assert b.billed_base         == 2_370_000
    assert b.recognised_profit   ==   232_000
    assert round(b.effective_markup, 4) == 0.0841
    assert b.deviation           ==    44_000

def test_act_two_factors_reconcile():
    assert 31_000 + 8_000 + 5_000 == 44_000

def test_act_one_strata_reconcile():
    assert sum([612_000, 384_000, 206_000, 290_000, 263_000, 92_000]) == 1_847_000

def test_clearing_ledger_sums_to_balance():
    assert load_clearing_ledger()["amount_usd"].sum() == 1_847_000

def test_plug_months_correlate_with_late_payroll():
    assert count_plug_months_with_late_payroll() == 7
```

### Exit criterion
`pytest tests/test_canonical_numbers.py` passes with zero failures. **Do not proceed otherwise.**

### Cut list
1. Reduce the untraceable stratum from 12 rows to 4 (keep the total at $92,000).
2. Replace the generated PDF memo with a `.txt` file. Note in the pitch that PDF parsing is a swap-in.

---

## PHASE 2 — Deterministic decomposition engine
**Hours 1:15 – 3:00**

### Objective
Build the financial core: all arithmetic, the exclusivity guarantee, the residual tracker, the materiality gate, and the disposition router. **No LLM in this phase.** Every canonical number must be reproducible by calling pure Python functions.

### Deliverables

**`engine/baseline.py`**
```python
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

def compute_baseline(entity_id: str, period: str) -> Baseline: ...
```

**`engine/decomposition.py`**
```python
class DecompositionState:
    """Owns the residual and the accepted transaction sets.
       This class is the audit guarantee. Treat it as such."""

    def __init__(self, opening_amount: Decimal, materiality: Decimal): ...

    def test_hypothesis(self, cause_id, classification,
                        transaction_ids, evidence_refs) -> HypothesisResult:
        # 1. exclusivity: reject if transaction_ids ∩ any accepted set
        # 2. resolve α from classification (never from caller input)
        # 3. factor = α × Σ amounts of transaction_ids
        # 4. materiality gate: reject if |factor| < threshold
        # 5. on accept: record set, decrement residual, emit AO message
        ...

    @property
    def residual(self) -> Decimal: ...
    @property
    def is_fully_explained(self) -> bool: ...
    def audit_trail(self) -> list[dict]: ...
```

Use `Decimal` throughout. Floats will produce `$4,999.9999999` in the demo.

**`engine/dispositions.py`** — maps `classification → (treatment, requires_approval, escalation_destination)` per the tables in Section 2.4 and 4.2.

**`engine/journal.py`** — builds balanced JE payloads. Assert debits equal credits before returning.

### Acceptance test

```python
def test_exclusivity_blocks_double_counting():
    s = DecompositionState(Decimal("44000"), Decimal("500"))
    s.test_hypothesis("F1", "TIMING_UNBILLED", ["GL-2026-0307"], [])
    r = s.test_hypothesis("F2", "MISCLASSIFICATION", ["GL-2026-0307"], [])
    assert r.accepted is False
    assert r.rejection_reason == "TRANSACTION_SET_OVERLAP"
    assert "GL-2026-0307" in r.conflicting_ids

def test_materiality_gate():
    s = DecompositionState(Decimal("5000"), Decimal("500"))
    r = s.test_hypothesis("H3", "FX_REVALUATION", ["GL-2026-0309"], [])
    assert r.accepted is False
    assert r.rejection_reason == "BELOW_MATERIALITY"
    assert s.residual == Decimal("5000")

def test_full_act_two_run_without_llm():
    s = DecompositionState(Decimal("44000"), Decimal("500"))
    s.test_hypothesis("F1", "TIMING_UNBILLED",    ["GL-2026-0307"], [])
    assert s.residual == Decimal("13000")
    s.test_hypothesis("F2", "APPROVED_EXCLUSION", ["GL-2026-0306"], [])
    assert s.residual == Decimal("5000")

def test_journal_entries_balance():
    je = draft_reclass(Decimal("140000"), "6100", "6800")
    assert sum(l.debit for l in je.lines) == sum(l.credit for l in je.lines)
```

### Exit criterion
Both acts produce their canonical numbers end to end with the LLM stubbed out. **This is the single most important gate in the plan.** From here, if the LLM misbehaves in the demo you can fall back to scripted hypothesis order and still show correct financials.

### Cut list
1. Simplify `journal.py` to a dict template rather than a typed builder.
2. Collapse `dispositions.py` into a module-level constant map.

---

## PHASE 3 — Agent layer and the two-act loop
**Hours 3:00 – 5:45**

### Objective
Add the cognitive layer: tools, ReAct loop, hypothesis generation, Act I orchestration, cause profile derivation, Act II orchestration reading that profile, and escalation.

### Deliverables

**`agent/tools.py`** — all seven tools per Section 5.2, each Neatlogs-decorated and returning `evidence_refs`.

**`agent/model.py`** — Tensormux client with two named routes:
```python
def call_fast(messages, tools=None):   # bulk classification
def call_strong(messages, tools=None): # policy reasoning, memos
```
Track call counts and cost per route in a module-level counter surfaced to the API.

**`agent/loop.py`** — ReAct loop with:
- hard step cap `MAX_STEPS = 12`, forced `escalate()` on breach
- every step emitting a state event to the WebSocket
- every step emitting an AO message
- structured tool-call parsing with a retry-once-then-escalate policy on malformed output

**`agent/prompts.py`** — the system prompt must state, in these terms:

> You do not calculate money. You identify which transactions belong to a cause and classify that cause. The engine computes every dollar figure. If you state a dollar amount in your reasoning, it is a hypothesis to be tested, never a result.

> When two sources disagree, apply the document precedence order in the policy. State which source you followed and which you overrode.

> If you cannot find evidence for a residual, escalate. Do not construct an explanation from plausibility. Name the specific document or system export that would resolve it.

**`agent/act_one.py`**
```
load clearing ledger
→ LLM proposes candidate strata from item metadata
→ for each candidate: call the confirming tool, gather evidence
→ pass transaction IDs to test_hypothesis()
→ assign disposition
→ after all strata: derive cause_profile.json from the plug stratum
→ escalate the untraceable remainder
```

**`agent/act_two.py`**
```
compute_baseline()
→ load cause_profile.json, order hypotheses by prior
→ emit event showing WHY this order (visible in UI)
→ test H1 timing → accept
→ test H2 approved exclusion → accept (precedence resolution)
→ test H3 FX → reject below materiality
→ test H4 misclassification → record as recovery, separate axis
→ residual $5,000 → draft true-up JE → escalate()
```

### Acceptance test
- Both acts complete from a single CLI entry point and print the canonical numbers.
- Run Act II three times. The **numbers** must be identical every time. Hypothesis phrasing may vary; results may not.
- Force a malformed tool call and confirm the loop retries once, then escalates rather than crashing.
- Confirm the rejected FX hypothesis appears in the Neatlogs trace.

### Exit criterion
`python -m agent.act_one && python -m agent.act_two` produces the complete, correct decomposition for both acts with a full audit trail.

### Cut list
1. Fix the Act I stratum order rather than having the LLM propose it; keep LLM confirmation of each. The interesting reasoning is in confirmation, not ordering.
2. Drop the retry policy; escalate on first malformed call.
3. Route everything to the strong model and hardcode the Tensormux routing display. **Cut this last** — the routing is a sponsor deliverable.

---

## Parallel Execution Plan: Phases 4 – 6 (Two-Track Split)

Phases 1 through 3 are complete. The remaining build (Phases 4–6, hours 5:45–10:00) is split across **two parallel tracks** executed simultaneously by two people within the existing time windows:

- **Track A — Ledger, backend & API:**
  - §6.1 Agent Orchestrator (mandatory), §6.4 Neatlogs
  - Phase 5: the FastAPI+WebSocket API layer (`api/main.py`, `api/events.py` per Appendix B schema — noted in Section 5.1 as a component, itemized explicitly under Phase 5 deliverables), `TraceStream.jsx`, `EvidenceCard.jsx`, `ApprovalModal.jsx` (these three surface AO/Neatlogs data)
  - Phase 6: graceful-degradation checks for AO + Neatlogs specifically, verifying AO ledger via `GetLedger`, opening the Neatlogs trace and finding the rejected FX span, the replay-fixture backend wiring, and the 30-second verification appendix recording
- **Track B — Payments, cost, console experience & delivery:**
  - §6.3 Dodo Payments, §6.5 Tensormux cost meter, §6.6 AI Grants voice (optional)
  - Phase 5: `StrataColumn.jsx`, `ResidualWaterfall.jsx`, `CostMeter.jsx`, the overall `App.jsx` shell/layout/design system per the mockup and "Design direction" guidance
  - Phase 6: graceful-degradation checks for Dodo + Tensormux + voice, the three timed dry runs, and demo capture/recording per Section 8
- **Shared / Joint Reference Material:**
  - `tests/test_attacks.py` (10 scenarios in §10.2 — mostly exercises engine/agent logic already built in Phase 1–3; either track can own it, note it needs coordination between both tracks).
  - Sections 8 (Demo script), 9 (Judge Q&A), 10.1 (Top risks), and 10.3 (Do-not-build list) remain shared reference material used by both tracks — preserved intact below.
- **Timing & Windows:** Both tracks work concurrently within each phase's existing window (5:45–10:00 total) rather than extending total time. Exit criteria are joint: both tracks must hit their respective gates together before moving to the next phase.

---

## PHASE 4 — Sponsor integration layer
**Hours 5:45 – 7:00**

### Objective
Wire AO, Neatlogs, Dodo, and the Tensormux cost meter so that each produces on-screen evidence a judge can independently verify.

### Deliverables

#### Track A:
**Agent Orchestrator (priority 1 — mandatory).**
- Deploy `ao/reconfx_ledger.lua` to a local `aos` process
- `integrations/ao_client.py` with a non-blocking send queue and a 2-second timeout
- Every `test_hypothesis()` result and every controller decision sends a message
- Record the process ID into the API config for the console header
- Verify by querying `GetLedger` and confirming every step is present

**Neatlogs (priority 2).**
- `neatlogs.init()` at API startup
- Spans on all seven tools plus `generate_hypotheses` and `test_hypothesis`
- Surface the live trace URL through the API for the console header
- All calls wrapped in `try/except`

#### Track B:
**Dodo Payments (priority 3).**
- `integrations/dodo_client.py`, test mode
- `create_collection(customer_ref, amount_usd, description)` returning a hosted link
- Wired to the Act I stratum-5 approval action only
- Failure path returns a stub link and logs; it must never block the demo

**Tensormux cost meter (priority 4).**
- Expose per-route call counts and cost through the API
- Format for the console footer

**AI Grants India voice (priority 5, optional).**
- Generate a spoken escalation briefing from the escalation packet
- Play in the console on escalation

### Acceptance test

#### Track A:
- Query the AO process directly and confirm the step list matches the console.
- Open the Neatlogs trace and locate the rejected FX span.

#### Track B:
- Open the Dodo test link in a browser.

#### Joint:
- Kill the network. Both acts still complete with correct numbers; integration failures are logged, not fatal.

### Exit criterion
**Joint (both tracks):** All four mandatory integrations produce verifiable artifacts, and every one degrades gracefully.

### Cut list

#### Track A:
4. **Never cut AO.** The organisers will inspect for it specifically.

#### Track B:
1. Voice briefing (cut first).
2. Cost meter becomes a static computed figure.
3. Dodo becomes a stub link with the API call shown in code during the demo.

---

## PHASE 5 — Controller console
**Hours 7:00 – 8:45**

### Objective
One screen, two acts, no navigation. Every number on screen arrives from the backend over WebSocket. Nothing is computed in the browser.

### Layout

```
┌──────────────────────────────────────────────────────────────────────┐
│ ENT-IN-02 → ENT-US-01 · March 2026 close                             │
│ AO process: ····  ·  Neatlogs trace: ····         [ Excavate | Close ]│
├───────────────────────────────┬──────────────────────────────────────┤
│                               │                                      │
│  AGENT TRACE                  │  ACT I — the clearing account        │
│                               │                                      │
│  query_clearing_account()     │  1900 · $1,847,000 · 38 months       │
│    → 55 open items            │                                      │
│  LEARN                        │  ┌────────────────────────────────┐  │
│  Hypothesis: cutover residue  │  │ 2023  cutover      $612,000    │  │
│    evidence: migration_log    │  │ 2023  FX unreversed $384,000   │  │
│    ✓ accepted   $612,000      │  │ 2024  duplicates    $206,000   │  │
│                               │  │ 2024  margin plugs  $290,000 ◀ │  │
│  ...                          │  │ 2024  collectible   $263,000 ↑ │  │
│                               │  │ ————  untraceable    $92,000 ! │  │
│  ─────────── bridge ────────  │  └────────────────────────────────┘  │
│                               │                                      │
│  RUN                          │  ACT II — this month                 │
│  Prior from 11 plug months:   │                                      │
│  timing 0.64 → test first     │  $44,000 ──┐                         │
│  query_payroll()              │            ├─ 31,000 timing          │
│    → PAY-2026-M2 posted 03-28 │  $13,000 ──┤                         │
│    → cutoff day 25            │            ├─  8,000 exclusion       │
│    ✓ accepted    $31,000      │  $ 5,000 ──┤                         │
│                               │            ✗    340 FX — rejected    │
│  ...                          │  $ 5,000  ESCALATE                   │
│  ESCALATE                     │                                      │
│  residual $5,000              │  ┌────────────────────────────────┐  │
│  evidence gap: billing-run    │  │ +$14,000 recovered entitlement │  │
│  config export, March 2026    │  └────────────────────────────────┘  │
│                               │                                      │
├───────────────────────────────┴──────────────────────────────────────┤
│ Fast 6 · Strong 4 · $0.--        [ Review escalation ]               │
└──────────────────────────────────────────────────────────────────────┘
```

### Design direction

The subject is forensic accounting: excavation, strata, evidence. Ground the visual language there and resist the defaults that make generated interfaces recognisable — the cream-and-terracotta palette, all-caps eyebrow labels above every heading, identical rounded cards with the same soft shadow, arrows appended to button text, tracked-out monospace micro-labels used decoratively.

Specific direction:

- **Spend boldness in one place: the strata column.** Act I's six bands should read as a geological section — bands sized by dollar amount, ordered by depth in time, with the oldest at the bottom. Everything else on the page stays quiet. This is the single memorable image of the demo.
- **Depth is the organising metaphor, so let vertical position carry meaning.** Older strata sit lower. The Act II waterfall descends. A viewer should understand the layout before reading a word.
- **Two type roles at most.** A neutral text face for the trace stream, and one distinct face for figures. Give the money its own treatment — tabular figures, aligned decimals — because in this product the numbers are the content.
- **Motion answers actions only.** One orchestrated reveal as each stratum confirms, and the waterfall stepping down as factors are accepted. No hover transitions on cards, no fade-and-slide entrances on every section.
- **Colour carries disposition, not decoration.** Explained, recovered, and escalated need three distinguishable states, and escalation should be the only place a high-alarm colour appears on the page. Do not rely on colour alone — each state carries a text label too.
- **Copy is plain and active.** "Approve true-up" produces "True-up approved." The escalation empty state says what evidence is missing, not that something went wrong.

### Deliverables

#### Track A:
- The FastAPI+WebSocket API layer (`api/main.py`, `api/events.py` per Appendix B schema — noted in Section 5.1 as a component, itemized explicitly here to surface AO/Neatlogs data to the console)
- `TraceStream.jsx` — append-only event log with tool calls, evidence refs, accept/reject markers, AO message IDs
- `EvidenceCard.jsx` — for each factor: transaction IDs, source documents, classification, disposition, AO message ID
- `ApprovalModal.jsx` — the draft true-up JE, evidence chain, evidence gap statement, approve / reject

#### Track B:
- The overall `App.jsx` shell/layout/design system per the mockup and "Design direction" guidance
- `StrataColumn.jsx` — Act I strata, each expandable to its evidence card
- `ResidualWaterfall.jsx` — Act II stepped descent, with the rejected hypothesis shown as a struck-through step
- `CostMeter.jsx` — Tensormux route counts

### Acceptance test

#### Track A:
- The approve action reaches AO and returns a confirmation.

#### Track B:
- A full run streams end to end with no manual refresh.
- Every displayed figure matches Section 4.
- The recovery finding is visually distinct from residual reductions.

#### Joint:
- A full run streams end to end with no manual refresh.
- Every displayed figure matches Section 4.
- The approve action reaches AO and returns a confirmation.
- The recovery finding is visually distinct from residual reductions.

### Exit criterion
**Joint (both tracks):** The full two-act narrative is watchable on one screen without the operator touching a terminal.

### Cut list

#### Track A:
1. Evidence cards become tooltips.
4. **Never cut the approval modal.** It is the human-judgment criterion made visible.

#### Track B:
2. `StrataColumn` becomes a styled table (keep the depth ordering).
3. Cost meter becomes static text.

---

## PHASE 6 — Hardening, dry runs, capture
**Hours 8:45 – 10:00**

### Objective
Make the demo unbreakable and record it. Build nothing new.

### Deliverables

#### Shared / Joint:
- Run `tests/test_attacks.py` covering the scenarios in Section 10.2 (mostly exercises engine/agent logic already built in Phase 1-3, either track can own it, note it needs coordination)

#### Track A:
**Hardening (0:45)**
- Confirm graceful degradation with each integration disabled in turn (graceful-degradation checks for AO + Neatlogs specifically)
- Verify AO ledger via `GetLedger` (querying the aos process terminal directly to confirm all steps and decisions)
- Open the Neatlogs trace and locate the rejected FX span
- Set a fixed model temperature and cache the successful run's tool outputs as a replay fixture
- Add `--replay` to the CLI, replaying the fixture with real timing but no network. **This is the demo insurance policy.**

**Capture (0:15)**
- Record a 30-second appendix: the aos terminal `GetLedger` query and the Neatlogs trace, for judges who want to verify

#### Track B:
**Hardening (0:45)**
- Confirm graceful degradation with each integration disabled in turn (graceful-degradation checks for Dodo + Tensormux + voice)

**Dry runs (0:15)**
- Three full runs, timed. Target 2:50 to leave headroom.
- Note every point where the operator has to touch something. Eliminate each one.

**Capture (0:15)**
- Record the 3-minute demo per Section 8

### Acceptance test

#### Track A:
- Confirm graceful degradation with AO and Neatlogs disabled.
- Query AO process directly via `GetLedger` and confirm step list matches console.
- Open Neatlogs trace and find the rejected FX span.
- Verify `--replay` flag runs fixture with real timing and no network.

#### Track B:
- Confirm graceful degradation with Dodo, Tensormux, and voice disabled.
- Three full runs, timed under 2:50 with zero operator touchpoints.
- 3-minute demo recorded per Section 8.

#### Joint:
- Run `tests/test_attacks.py` covering the scenarios in Section 10.2 with zero failures.

### Exit criterion
**Joint (both tracks):** The recorded demo exists and runs to completion without operator intervention. Submit it. Do not keep polishing.

### Cut list

#### Track A:
- Skip live aos recording if short on time; fall back to static terminal screenshot.

#### Track B:
- Cut third dry run if runs 1 and 2 are clean; do not over-polish video transitions.

---

# Section 8 — Demo script

**3:00 total. Rehearse to 2:50.**

| Time | Screen | Narration |
|---|---|---|
| 0:00–0:18 | March close, deviation alert, $44,000 | "It's March close. The India entity's margin came in at 8.41% against a 10% policy. Forty-four thousand dollars off. Standard practice is to post a true-up or accrue it to the clearing account. Before we do either — where does that accrual actually go?" |
| 0:18–0:35 | Cut to account 1900: $1,847,000, oldest item 38 months, owner unassigned | "Here. Account 1900. One-point-eight million dollars, oldest item three years old, no owner. Every finance team has this account and nobody can tell you what's in it." |
| 0:35–1:25 | Strata confirm one by one; column builds | "reconFX excavates it. Six hundred twelve thousand from the 2023 NetSuite cutover, matched against the migration log. Three eighty-four in FX revaluations that never reversed. Two-oh-six in a duplicated vendor feed — fourteen entries, same invoice reference, same day. Two sixty-three is a live customer receivable that stopped being invoiced in August 2024. And ninety-two thousand it cannot explain — so it says so, and lists the evidence that would close it." |
| 1:25–1:42 | Margin plug stratum highlights; bridge line appears | "And this one. Two hundred ninety thousand across eleven months, described as margin plugs. Eleven times, a controller couldn't explain a variance and accrued it away. In seven of those eleven months, payroll posted after the billing cutoff. This month's forty-four thousand is about to become the twelfth." |
| 1:42–2:25 | Act II waterfall descends | "So it investigates instead. It tests timing first — because the history says timing, sixty-four percent. Three hundred ten thousand of payroll, March service period, posted the 28th. Cutoff is the 25th. Thirty-one thousand explained as timing, not pricing. Eighty thousand of severance the billing engine blocked and the margin monitor counted — approval memo EXP-2026-08 says permanently excluded, so the billing engine was right. Eight thousand. It tests FX, finds three hundred forty dollars, rejects it as immaterial, and logs the rejection." |
| 2:25–2:45 | Escalation modal; recovery card | "Five thousand left. It won't invent a cause for it. Effective rate applied was 9.79% against a 10% contract — probable, not proven, because the billing-run config isn't available. So it drafts the true-up and escalates, naming exactly which export would close it. And separately: a hundred forty thousand of engineering software sitting in an excluded account. Fourteen thousand this entity was entitled to bill and never did." |
| 2:45–3:00 | Approve; AO ledger and prior update render | "The controller approves. It commits to the Agent Orchestrator ledger, immutably. The prior updates for April. Last month, forty-four thousand would have gone into that account. This month, five thousand goes to a human with evidence — and nothing gets buried." |

**Rules for delivery.** Never say "AI-powered." Never explain the architecture. Let the strata column and the descending waterfall do the work. The two sentences that must land clearly are the bridge ("this month's is about to become the twelfth") and the close ("nothing gets buried").

---

# Section 9 — Judge questions and answers

**"Isn't the excavation a one-time cleanup?"**
Yes, and that is the design. The excavation clears the past and produces the entity's failure profile; the monthly investigation stops the profile from growing. Run once to bury the past, run monthly so there is no future to excavate. The one-time job pays for the permanent one.

**"Maximor already does flux analysis and intercompany elimination."**
It does, and we make no claim otherwise. Maximor explains variance at the financial-statement line level from GL activity. reconFX explains it at the operational-event level, joining payroll posting timestamps, billing-run cutoff configuration, and approval memo prose — sources a GL-driven flux engine does not read. The output is a JE payload Maximor could ingest. It is a layer, not a competitor.

**"EXA and CCH Tagetik do operational transfer pricing."**
They detect the breach and compute the true-up. Neither decomposes the breach before computing it. That distinction is the whole product: EXA would post $44,000 here. Thirty-nine thousand of that is timing, an approved exclusion, and a system disagreement — none of it a taxable price adjustment. Posting it creates the exposure it was meant to prevent.

**"How do you know the agent isn't hallucinating the numbers?"**
It cannot. The model returns transaction IDs and a classification. Every dollar figure comes from a deterministic Python function that sums those transactions and applies a rate fixed by the classification. The engine also enforces set disjointness, so a transaction cannot be counted twice even if the model tries. Here is the test that proves it. [Show `test_exclusivity_blocks_double_counting`.]

**"What if it explains something wrongly?"**
Three defences. Materiality: anything below threshold is rejected, as the FX hypothesis was. Precedence: when sources conflict, it applies the policy's stated document hierarchy and records which source it overrode. And escalation: it never auto-posts a genuine deviation. The $5,000 stops and waits for a human, with a named evidence gap.

**"Why didn't it explain the whole $1.8 million?"**
Because it can't, and an agent that claimed otherwise would be lying. Ninety-two thousand has no trail in the available systems. It says so and lists what would resolve it. That is the answer a controller can take to an auditor.

**"Where is Agent Orchestrator actually used?"**
Every factor, every rejection, and every controller decision is a message to an aos process — append-only, externally verifiable. The agent cannot rewrite its own reasoning after the fact, which is precisely the property a tax authority requires. [Query the process live.]

**"Could a person do this?"**
For one entity-month, yes — four to eight hours. For 38 months of a clearing account, correlating plug entries against payroll posting patterns across three years, nobody does it. Not because it's hard, but because nobody has ever been given the time. That balance is what "we'll get to it" looks like after three years.

---

# Section 10 — Risks, attacks, and the do-not-build list

## 10.1 Top risks

| Risk | Mitigation |
|---|---|
| LLM produces a wrong dollar figure | Structurally impossible: the model never returns money. Phase 2 gate. |
| Agent double-counts a transaction | Exclusivity constraint in `test_hypothesis()`. Tested in Phase 2. |
| AO network latency stalls the loop | Non-blocking send queue, 2s timeout, local `aos` during recording |
| Neatlogs rate limit breaks the run | All tracing in `try/except` |
| Live demo fails on stage | `--replay` fixture built in Phase 6. Record the demo; do not present live. |
| Agent loops indefinitely | `MAX_STEPS = 12`, forced escalation on breach |
| UI state desync | Single WebSocket event stream, no browser-side computation |
| Dataset inconsistency found late | Phase 1 gate, re-run at every phase boundary |
| Scope creep in Phase 5 | Cut list is ordered and non-negotiable |

## 10.2 Attack scenarios for `tests/test_attacks.py`

*(Shared / Joint: exercises engine and agent logic already built in Phases 1–3; either track can own it, requires coordination between Track A and Track B)*

| # | Scenario | Required behaviour |
|---|---|---|
| 1 | Same transaction claimed by two hypotheses | Second rejected, `TRANSACTION_SET_OVERLAP`, conflicting IDs returned |
| 2 | Exception memo caps at $50,000 but GL shows $80,000 | Factor caps at $50,000; remaining $30,000 stays in residual |
| 3 | GL description says "rechargeable" but the account is excluded | Flags the mapping conflict; applies precedence; records the override explicitly |
| 4 | Policy markup changes mid-period | Checks posting date against policy effective range before applying a rate |
| 5 | Factor computed below materiality | Rejected and logged, residual unchanged |
| 6 | Approval memo link unresolvable | Fails evidence verification; does not accept the factor; escalates |
| 7 | Duplicate GL doc ID | Duplicate detector fires; drafts a reversal; excludes from base |
| 8 | Malformed tool call from the model | Retry once, then escalate. Never crash. |
| 9 | Residual goes negative (over-explanation) | Halt immediately; flag `OVER_ATTRIBUTION`; escalate |
| 10 | Clearing ledger row belongs to a third entity | Cost-centre entity tag inspected; excluded from this entity's decomposition |

## 10.3 Do not build

These will feel tempting. They are all out of scope.

- Multi-entity consolidation or currency translation
- A second entity pair or a second period
- Real ERP connectors (mock everything through JSON and CSV)
- Authentication, users, or roles
- An agent framework (LangGraph, CrewAI, AutoGen)
- A predictive or pre-filing anomaly engine — one line of future work, no code
- Vector search or RAG over the evidence corpus (ten files; direct queries are faster and more auditable)
- A settings screen, a dark-mode toggle, or a landing page
- Anything using the word "dashboard" that isn't the two panels in Section 5

---

# Appendix A — Hour-by-hour

| Hours | Phase | Gate |
|---|---|---|
| 0:00–1:15 | 1 · Evidence corpus | `test_canonical_numbers.py` green |
| 1:15–3:00 | 2 · Deterministic engine | Both acts correct with no LLM |
| 3:00–5:45 | 3 · Agent layer | Both acts run end to end from CLI |
| 5:45–7:00 | 4 · Sponsors | AO verified on chain; Neatlogs trace open; Dodo link live |
| 7:00–8:45 | 5 · Console | Full narrative watchable on one screen |
| 8:45–10:00 | 6 · Harden and capture | Demo recorded and submitted |

**Hard rule:** if Phase 2 is not green by 3:15, stop everything and finish it. A correct engine with a plain terminal UI beats a beautiful console showing wrong numbers, in front of accountants, every single time.

# Appendix B — Event schema

Every backend event on the WebSocket:

```json
{
  "event_type": "TOOL_CALL | HYPOTHESIS | FACTOR_ACCEPTED | FACTOR_REJECTED |
                 RECOVERY_FOUND | DISPOSITION | ESCALATION | DECISION | COST",
  "act": "EXCAVATION | INVESTIGATION",
  "timestamp": "2026-03-31T10:14:22Z",
  "step": 4,
  "payload": {
    "cause_id": "F1",
    "label": "Unbilled late payroll",
    "classification": "TIMING_UNBILLED",
    "transaction_ids": ["GL-2026-0307"],
    "evidence_refs": ["payroll_register.csv#PAY-2026-M2",
                      "tp_policy.json#billing_cutoff_day_of_month"],
    "factor_usd": 31000.00,
    "residual_before": 44000.00,
    "residual_after": 13000.00,
    "disposition": "ROLL_TO_APRIL_BILLING",
    "requires_approval": false,
    "ao_message_id": "...",
    "neatlogs_span_id": "..."
  }
}
```

# Appendix C — Escalation packet schema

```json
{
  "escalation_id": "ESC-2026-03-001",
  "entity_id": "ENT-IN-02",
  "period": "2026-03",
  "opening_deviation_usd": 44000.00,
  "explained_usd": 39000.00,
  "residual_usd": 5000.00,
  "factors": [ /* full factor records with evidence chains */ ],
  "rejected_hypotheses": [
    { "hypothesis": "FX_REVALUATION", "computed_impact_usd": 340.00,
      "rejection_reason": "BELOW_MATERIALITY", "threshold_usd": 500.00 }
  ],
  "recovery_findings": [
    { "label": "Misclassified rechargeable software",
      "amount_usd": 140000.00, "entitlement_impact_usd": 14000.00,
      "proposed_entry": "Dr 6100 / Cr 6800 $140,000" }
  ],
  "probable_cause": "Effective markup 9.79% applied against contractual 10.00% on billed base $2,370,000",
  "confidence": "PROBABLE_UNPROVEN",
  "evidence_gap": [
    "March 2026 billing-run configuration export (markup rate parameter)",
    "Billing engine change log for period 2026-03-01 to 2026-03-25"
  ],
  "proposed_journal_entry": {
    "type": "TP_TRUE_UP",
    "status": "DRAFT",
    "requires_approval": true,
    "lines": [
      { "entity": "ENT-IN-02", "account": "1200", "description": "Intercompany Receivable - US Parent", "debit": 5000.00 },
      { "entity": "ENT-IN-02", "account": "4100", "description": "Intercompany Service Revenue", "credit": 5000.00 },
      { "entity": "ENT-US-01", "account": "6300", "description": "Intercompany Engineering Expense", "debit": 5000.00 },
      { "entity": "ENT-US-01", "account": "2100", "description": "Intercompany Payable - India Sub", "credit": 5000.00 }
    ]
  },
  "ao_ledger_reference": "...",
  "neatlogs_trace_url": "..."
}
```
