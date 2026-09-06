# reconFX — Demo Runbook & Operator Script

**Duration:** 3:00 Total (Rehearse to 2:50) + 0:30 Verification Appendix  
**Target:** Hackathon Recording / Live Demonstration  
**Applicable Branch:** `phase6-dryrun` (or merged `main`)

---

## 1. Rules for Delivery

1. **Never say "AI-powered."**
2. **Never explain the architecture.** Let the geological strata column and descending waterfall do the work.
3. **The two load-bearing sentences that must land crisply:**
   - **The Bridge (1:40):** *"In seven of those eleven months, payroll posted after the billing cutoff. This month's forty-four thousand is about to become the twelfth."*
   - **The Close (2:55):** *"Last month, forty-four thousand would have gone into that account. This month, five thousand goes to a human with evidence — and nothing gets buried."*

---

## 2. Pre-Flight Checklist

Ensure the following prerequisites are met before hitting record:

- [ ] **Node dependencies installed:**
  ```bash
  cd ui && npm ci
  ```
- [ ] **Python environment ready:**
  ```bash
  python3 -m pip install -r requirements.txt
  ```
- [ ] **Port availability:** Verify ports `8000` (FastAPI) and `5173` (Vite) are available:
  ```bash
  ss -tulpn | grep -E ':8000|:5173' || lsof -i :8000 -i :5173
  ```
  *(If occupied, terminate previous processes or adjust ports).*
- [ ] **Browser setup:** Chrome/Firefox opened at `1920x1080` (100% zoom), dev tools closed.

---

## 3. Server Startup Sequence

Always start the backend API first, followed by the frontend Vite dev server.

### Terminal 1 — Backend API
```bash
# In repo root: /path/to/reconfx
python3 -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```
*Expected output:*
```text
INFO:     Started server process [...]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

### Terminal 2 — Controller Console UI
```bash
cd ui
npm run dev
```
*Expected output:*
```text
  VITE v5.4.21  ready in ~400 ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: http://...
```

### Browser Navigation
Open `http://localhost:5173` in your browser.  
Confirm the header shows:
- Title: `ENT-IN-02 → ENT-US-01` · `March 2026 close`
- Status dot: Green `live stream` (if connected to WebSocket) or Amber `offline / local fixture` (graceful fallback).

---

## 4. Timed Demo Script (0:00 – 3:00)

| Time | Screen / Operator Action | Verbatim Narration | Visual Checkpoint |
| :--- | :--- | :--- | :--- |
| **0:00 – 0:18** | **Screen:** Console Header & Act II Section.<br>**Action:** Mouse hovers briefly over header badge `March 2026 close` and opening variance `$44,000`. | *"It's March close. The India entity's margin came in at 8.41% against a 10% policy. Forty-four thousand dollars off. Standard practice is to post a true-up or accrue it to the clearing account. Before we do either — where does that accrual actually go?"* | Header displays entity pair `ENT-IN-02 → ENT-US-01` and opening variance `$44,000`. |
| **0:18 – 0:35** | **Screen:** Act I Section (Right Column, Top).<br>**Action:** Switch view or focus on **Act I — The Clearing Account** header (`1900 · $1,847,000 · 38 months`). | *"Here. Account 1900. One-point-eight million dollars, oldest item three years old, no owner. Every finance team has this account and nobody can tell you what's in it."* | Section header displays `$1,847,000` balance across 38 months. |
| **0:35 – 1:25** | **Screen:** Act I Strata Column.<br>**Action:** Click on strata from bedrock upwards to reveal details in `EvidenceCard` on the left:<br>1. Click `$612,000` (cutover)<br>2. Click `$384,000` (FX reval)<br>3. Click `$206,000` (duplicates)<br>4. Click `$263,000` (collectible receivable)<br>5. Click `$92,000` (untraceable). | *"reconFX excavates it. Six hundred twelve thousand from the 2023 NetSuite cutover, matched against the migration log. Three eighty-four in FX revaluations that never reversed. Two-oh-six in a duplicated vendor feed — fourteen entries, same invoice reference, same day. Two sixty-three is a live customer receivable that stopped being invoiced in August 2024. And ninety-two thousand it cannot explain — so it says so, and lists the evidence that would close it."* | 5 strata bands confirm: bedrock cutover, FX reval, duplicate feed, collectible receivable, and untraceable red badge. |
| **1:25 – 1:42** | **Screen:** Margin Plug Stratum & Bridge Line.<br>**Action:** Click the highlighted `$290,000` stratum (marked `◀ bridge`). Observe the bridge indicator connecting Act I to Act II. | *"And this one. Two hundred ninety thousand across eleven months, described as margin plugs. Eleven times, a controller couldn't explain a variance and accrued it away. In seven of those eleven months, payroll posted after the billing cutoff. This month's forty-four thousand is about to become the twelfth."* | `$290,000` stratum is visually highlighted with amber/green accent; bridge prior (0.64) connects to Act II. |
| **1:42 – 2:25** | **Screen:** Act II Waterfall.<br>**Action:** Shift focus down to **Act II — This Month** stepped waterfall.<br>1. Hover on Step 1: `$31,000` timing reduction.<br>2. Hover on Step 2: `$8,000` approved exclusion.<br>3. Hover on Step 3: `$340` struck-through FX rejection. | *"So it investigates instead. It tests timing first — because the history says timing, sixty-four percent. Three hundred ten thousand of payroll, March service period, posted the 28th. Cutoff is the 25th. Thirty-one thousand explained as timing, not pricing. Eighty thousand of severance the billing engine blocked and the margin monitor counted — approval memo EXP-2026-08 says permanently excluded, so the billing engine was right. Eight thousand. It tests FX, finds three hundred forty dollars, rejects it as immaterial, and logs the rejection."* | Stepped waterfall descends: `$44,000` → `$13,000` → `$5,000`. Struck-through line confirms `$340` FX rejection. |
| **2:25 – 2:45** | **Screen:** Independent Recovery Axis & Escalation Review.<br>**Action:**<br>1. Point mouse to the green `+$14,000` recovery card (`$140,000` SaaS reclass).<br>2. Click **"Review escalation"** in footer to open `ApprovalModal`. | *"Five thousand left. It won't invent a cause for it. Effective rate applied was 9.79% against a 10% contract — probable, not proven, because the billing-run config isn't available. So it drafts the true-up and escalates, naming exactly which export would close it. And separately: a hundred forty thousand of engineering software sitting in an excluded account. Fourteen thousand this entity was entitled to bill and never did."* | Modal displays: Missing evidence gap (billing export), draft journal entry lines debiting 1200 / crediting 4100. |
| **2:45 – 3:00** | **Screen:** Approval Modal & Footer Status.<br>**Action:** Click **"Approve true-up"** button.<br>Modal closes; footer displays green `"True-up approved."` with AO ledger confirmation. | *"The controller approves. It commits to the Agent Orchestrator ledger, immutably. The prior updates for April. Last month, forty-four thousand would have gone into that account. This month, five thousand goes to a human with evidence — and nothing gets buried."* | Decision commits. Footer confirms immutable ledger append. |

---

## 5. 30-Second Verification Appendix (3:00 – 3:30)

For judges and technical reviewers requiring immutable verification of on-chain state and full distributed execution traces:

### 1. Agent Orchestrator (AO) Ledger Query (15s)
In an `aos` terminal connected to the deployed process:
```lua
Send({ Target = ao.id, Tags = { Action = "GetLedger" } })
```
or inspect the response payload:
```lua
Inbox[#Inbox].Data
```
**What to show on screen:**
- Show the raw JSON chain state returned from the contract.
- Highlight that every step (`S1` through `S6`, `F1`, `F2`, `H3`) and the controller's decision (`APPROVE_TRUEUP`) were committed immutably with timestamp and transaction IDs.

### 2. Neatlogs Distributed Trace (15s)
Click the **Neatlogs trace** link in the console header (`https://neatlogs.com/traces/...`).  
**What to show on screen:**
- The flamegraph / waterfall of spans (`EXCAVATION`, `INVESTIGATION`, tool executions).
- Show that no LLM call is ever passed raw money or returns dollar figures—demonstrating deterministic mathematical safety.

---

## 6. Environment & Feature Delta (What to Check Before Recording)

| Feature / Deliverable | Script Expectation | Current Build State in this Environment | Action / Workaround for Recording |
|---|---|---|---|
| **AO Ledger (`aos` terminal)** | Live `aos` query on camera (`GetLedger`) | `aos` CLI is **not pre-installed in `$PATH`** on this system; AO client runs in non-blocking mock/stub fallback mode. | If presenting live chain queries, install `aos` (`npm i -g https://github.com/permaweb/aos.git`), launch a local process with `ao/reconfx_ledger.lua`, and set `AO_PROCESS_ID`. If recording without `aos`, demonstrate the verified unit test `pytest tests/test_ao_client.py` on camera or show the Lua process code. |
| **Neatlogs Live Tracing** | Clicking header link opens live trace dashboard | `NEATLOGS_API_KEY` is unset in default environment; system uses placeholder trace URL `https://neatlogs.com/traces/tr-recon-20260331-01`. | If a live Neatlogs workspace is desired, export `NEATLOGS_API_KEY` in `.env`. Otherwise, the placeholder link renders cleanly in the UI header. |
| **Dodo Payments Link** | Payment link for customer receivable `$263,000` | Fallback generates test stub: `https://test.dodopayments.com/buy/pay_test_cust-4471_263000`. | The stub link is fully functional for demo clicks without requiring live credit card processing. |
| **Act I / Act II Triggering** | Streaming live events into UI | The UI renders the canonical dataset out-of-the-box upon launch. Live WebSocket streaming can also be triggered via background API calls. | To demonstrate live event streaming in real time, run `curl -X POST http://localhost:8000/api/run/act-one` and `curl -X POST http://localhost:8000/api/run/act-two` in a side terminal. The WebSocket stream will update the console dynamically. |

---

## 7. Emergency Fallback Procedure

If any network, backend, or sponsor service falters during rehearsal or presentation:
1. **Frontend Static Resilience:** The UI has built-in canonical data. Even if the FastAPI backend is completely offline, the UI will display the complete, verified figures ($1,847,000 clearing account, 6 strata, $44,000 opening deviation, descending waterfall, and approval modal).
2. **Deterministic CLI Verification:** If judges ask to verify the calculations live in a shell:
   ```bash
   python3 -m agent.act_one
   python3 -m agent.act_two
   ```
   Both will run in < 1.5s and output the exact canonical figures.
