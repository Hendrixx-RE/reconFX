# Phase 6: Dry Run Timing & Operator Touchpoint Report

**Date:** 2026-09-06  
**Environment:** Linux (x86_64), Python 3.14.7, Node v22.23.1, npm 10.9.8  
**Branch:** `phase6-dryrun`  
**Target:** reconFX Phase 6 Hardening, Dry Runs & Capture Deliverables

---

## 1. Executive Summary

This report documents the programmatic execution, timing measurements, determinism verification, and operator touchpoints for **reconFX** Act I (Excavation) and Act II (Investigation), meeting the requirements of README.md Phase 6 deliverables ("Dry runs" and "Capture").

Key findings:
- **CLI Cold-Start Wall-Clock Time:** Act I averages **0.746s**; Act II averages **0.713s**. Both acts execute in under **1.5 seconds combined**.
- **FastAPI In-Process Wall-Clock Time:** Act I averages **0.051s**; Act II averages **0.028s** (**< 0.08s combined**).
- **Presentation Headroom:** Rehearsal budget is **2:50** (170 seconds) against a **3:00** hard cap. Because computational execution is instantaneous (< 1.5s), 100% of the demo time is available for human narration and screen navigation with zero risk of processing lag.
- **Determinism:** 100% bit-exact across all repeated runs (reuses the Phase 2 exclusivity constraint and deterministic engine).
- **Operator Touchpoints:** 0 blocking CLI prompts found (`input()` is never called). Minor frontend prop contracts were aligned so that UI clicking on strata and waterfall nodes correctly activates the `EvidenceCard`. Graceful fallbacks exist for all external sponsor services (AO, Neatlogs, Dodo Payments).

---

## 2. Programmatic Dry Run Timings

All dry runs were executed programmatically using Python's high-precision `time.perf_counter()`.

### 2.1 CLI Execution (`python -m agent.act_one` & `python -m agent.act_two`)

| Run # | Act I: Excavation (`agent.act_one`) | Act II: Investigation (`agent.act_two`) | Total CLI Wall-Clock |
| :--- | :--- | :--- | :--- |
| **Run 1** | 0.7694 s | 0.7149 s | 1.4843 s |
| **Run 2** | 0.7459 s | 0.6959 s | 1.4418 s |
| **Run 3** | 0.7223 s | 0.7285 s | 1.4508 s |
| **Mean** | **0.7459 s** | **0.7131 s** | **1.4590 s** |
| **Min / Max** | 0.7223 s / 0.7694 s | 0.6959 s / 0.7285 s | — |

#### Act I CLI Output Verification (Identical Across Runs)
- **Opening Balance:** `$1,847,000.00`
- **Confirmed Strata:** 6
  1. `S1` ERP cutover artifacts: `$612,000.000` (9 transactions, disposition `WRITE_OFF_TO_PL`)
  2. `S2` Unreversed FX revaluations: `$384,000.000` (6 transactions, disposition `DRAFT_REVERSING_JE`)
  3. `S3` Duplicate AP vendor feed: `$206,000.000` (14 transactions, disposition `DRAFT_REVERSAL_OF_DUPLICATES`)
  4. `S4` Accrued IC margin plugs: `$290,000.000` (11 transactions across 11 months, seeds prior)
  5. `S5` Live collectible receivable: `$263,000.000` (3 transactions, customer CUST-4471, Dodo payment link generated)
  6. `S6` Untraceable remainder: `$92,000.000` (12 transactions, escalated with explicit missing evidence gap)
- **Residual After All Strata:** `$0.000`
- **Escalated:** `True` (Suspense residue escalated to corporate controller)

#### Act II CLI Output Verification (Identical Across Runs)
- **Opening Deviation:** `$44,000.000` (India entity ENT-IN-02 margin 8.41% vs. 10.00% target)
- **Prior Hypothesis Order:** Timing (0.64 prior, 7 of 11 months) → Exclusion → FX → Misclassification
- **Accepted Factors:** 2
  - `F1` Timing unbilled payroll: `$31,000.000` (Off-cycle payroll posted 03-28 after 03-25 cutoff; residual: `$13,000.000`)
  - `F2` Approved exclusion: `$8,000.000` (Severance memo EXP-2026-08 overrides GL mapping; residual: `$5,000.000`)
- **Rejected Hypotheses:** 1
  - `H3` FX revaluation: `$340.000` (Rejected: below `$500.00` materiality threshold; residual remains `$5,000.000`)
- **Recovery Findings (Independent Axis):** 1
  - `F4` Misclassified software: `$140,000.00` rechargeable SaaS stranded in GL 6800 → `$14,000.000` entitlement impact
- **Final Residual:** `$5,000.000` (Probable cause: effective markup 9.79% applied vs 10% contractual; missing billing config export)
- **Draft Journal Entry:** Balanced 4-line intercompany entry totaling `$5,000.00`
- **Escalated:** `True`

---

### 2.2 FastAPI Asynchronous Background Worker Timings

Triggered via HTTP POST endpoints against `http://127.0.0.1:8000`:

| Run # | `POST /api/run/act-one` | `POST /api/run/act-two` | Total API Execution |
| :--- | :--- | :--- | :--- |
| **Run 1** | 0.0793 s | 0.0298 s | 0.1091 s |
| **Run 2** | 0.0370 s | 0.0266 s | 0.0636 s |
| **Run 3** | 0.0365 s | 0.0269 s | 0.0634 s |
| **Mean** | **0.0509 s** | **0.0278 s** | **0.0787 s** |

*Note: In-process execution through FastAPI background worker threads avoids Python process cold-start, completing full end-to-end execution and event emission in < 80ms.*

---

## 3. Operator Touchpoints & Resolutions

Every point where a human operator or automated workflow interacts with the environment was audited:

| # | Touchpoint | Category | Impact | Status / Fix |
|---|---|---|---|---|
| 1 | **Missing `ui/node_modules`** | Environment / Setup | Running `npm run dev` or `npm run build` fails with `sh: vite: command not found` if dependencies are uninstalled. | **Documented in Runbook:** Operator must run `npm ci` inside `ui/` prior to running Vite dev or build. |
| 2 | **Server startup order** | Orchestration | UI connects to `ws://localhost:8000/ws/events`. If UI starts before API, the WebSocket indicator shows "offline / local fixture". | **Resolved & Documented:** UI automatically retries connection every 3s and falls back to canonical data without crashing. Runbook specifies launching API on port 8000 first, then UI. |
| 3 | **Port conflicts** | Networking | If port 8000 or 5173 is already in use by background processes, dev servers fail to bind. | **Documented in Runbook:** Include commands to verify port availability (`lsof -i :8000 -i :5173` or `ss -tulpn`). |
| 4 | **Interactive Strata click-through** | UI Component | `StrataColumn.jsx` expected `onExpandStratum` while `App.jsx` passed `onSelectStratum`, causing stratum clicks to not show `EvidenceCard`. | **Fixed directly:** Updated `StrataColumn.jsx` to accept `onSelectStratum` as an alias, restoring click-through inspection. |
| 5 | **Interactive Waterfall step click-through** | UI Component | `ResidualWaterfall.jsx` did not expose an `onSelectFactor` prop, preventing factor selection. | **Fixed directly:** Added `onSelectFactor` to `ResidualWaterfall.jsx` for factor steps and recovery cards. |
| 6 | **EvidenceCard dismissal** | UI Component | `EvidenceCard.jsx` did not have a close button to dismiss the card in the trace panel. | **Fixed directly:** Added `onClose` callback and close `✕` button to `EvidenceCard.jsx`. |
| 7 | **Controller approval backend sync** | UI / API | Approving or rejecting in `App.jsx` updated local state but didn't notify backend `/api/approve`. | **Fixed directly:** Connected `handleApprove` and `handleReject` in `App.jsx` to `fetch('http://localhost:8000/api/approve')` with non-blocking error handling. |
| 8 | **`aos` executable missing in environment** | Sponsor / External | `aos` binary is not present in `$PATH` in this environment; live chain interaction requires an active `aos` process. | **Documented in Runbook:** Detailed how to run the demo using canonical fallback vs. setting up local `aos` process with `reconfx_ledger.lua`. |
| 9 | **Sponsor API keys missing (`.env`)** | Integrations | `AO_PROCESS_ID`, `NEATLOGS_API_KEY`, `DODO_API_KEY`, `TENSORMUX_API_KEY`. | **Graceful Fallbacks Verified:** All integrations contain non-blocking fallbacks. Dodo generates a test stub link, AO queues drop silently without blocking, and Neatlogs provides fallback URLs. |
| 10 | **Blocking prompts (`input()`)** | Agent Execution | Any CLI prompt requiring operator keystrokes would stall automated recording. | **Verified:** 0 occurrences of `input()` in the entire codebase. Completely non-blocking. |

---

## 4. Whole-System Sanity Pass

### 4.1 Test Suite Baseline (`pytest tests/ -v`)
```text
tests/test_agent_loop.py::test_act_two_reproducible_across_runs PASSED
tests/test_agent_loop.py::test_act_two_factors_reconcile_to_44000 PASSED
tests/test_agent_loop.py::test_act_one_strata_reconcile_to_1847000 PASSED
tests/test_agent_loop.py::test_act_one_escalates_untraceable_stratum PASSED
tests/test_agent_loop.py::test_malformed_tool_call_retries_once_then_escalates PASSED
tests/test_agent_loop.py::test_loop_halts_at_step_cap PASSED
tests/test_ao_client.py::test_unconfigured_ao_client_noops PASSED
tests/test_ao_client.py::test_network_failure_is_non_fatal PASSED
tests/test_ao_client.py::test_act_one_and_act_two_events_wire_to_ledger PASSED
tests/test_ao_client.py::test_nonblocking_queue_timeout_resilience PASSED
tests/test_api.py::test_status_endpoint PASSED
tests/test_api.py::test_status_with_env_config PASSED
tests/test_api.py::test_approve_endpoint PASSED
tests/test_api.py::test_trigger_act_one_and_websocket_events PASSED
tests/test_api.py::test_trigger_act_two PASSED
tests/test_api.py::test_event_normalization_and_validation PASSED
tests/test_canonical_numbers.py::test_act_two_baseline PASSED
tests/test_canonical_numbers.py::test_act_two_factors_reconcile PASSED
tests/test_canonical_numbers.py::test_act_one_strata_reconcile PASSED
tests/test_canonical_numbers.py::test_clearing_ledger_sums_to_balance PASSED
tests/test_canonical_numbers.py::test_plug_months_correlate_with_late_payroll XFAIL
tests/test_exclusivity.py::test_exclusivity_blocks_double_counting PASSED
tests/test_exclusivity.py::test_materiality_gate PASSED
tests/test_exclusivity.py::test_full_act_two_run_without_llm PASSED
tests/test_exclusivity.py::test_over_attribution_is_rejected PASSED
tests/test_exclusivity.py::test_quantify_factor_does_not_touch_residual PASSED
tests/test_exclusivity.py::test_journal_entries_balance PASSED
tests/test_exclusivity.py::test_unbalanced_journal_entry_rejected PASSED

Results: 27 passed, 1 xfailed (expected Phase 1 canonical correlation gate) in 5.00s.
```

### 4.2 UI Production Build (`cd ui && npm run build`)
```text
> reconfx-ui@0.1.0 build
> vite build

vite v5.4.21 building for production...
transforming modules...
✓ 38 modules transformed.
rendering chunks...
dist/index.html                   0.73 kB │ gzip:  0.41 kB
dist/assets/index-C4qNG8fN.css    9.71 kB │ gzip:  2.23 kB
dist/assets/index-ChQIUZ3H.js   224.60 kB │ gzip: 63.69 kB
✓ built in 2.38s
```

### 4.3 API & UI Server Startup Verification
- **API Server:** `uvicorn api.main:app --port 8001` launched cleanly. `/api/status` returned HTTP 200 with JSON payload within 1 second. Cleanly terminated.
- **UI Dev Server:** `npm run dev -- --port 5174` launched Vite v5.4.21 in 483ms, served index HTML. Cleanly terminated.
