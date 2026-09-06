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
