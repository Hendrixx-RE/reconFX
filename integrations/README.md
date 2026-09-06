# integrations/ — Phase 4: sponsor integrations

**Status: not started.**

Per PLAN.md §6, each of these wraps a sponsor stack in a way a judge can
independently verify on screen, and each must degrade gracefully (never
block the demo) if the network or the sponsor's API is unavailable:

- `ao_client.py` — non-blocking send queue to the AO ledger (`ao/`),
  2-second timeout. **Priority 1, mandatory.**
- `neatlogs_setup.py` — `neatlogs.init()` plus span decorators on the 7
  tools in `agent/tools.py` (which already has a no-op `span()` placeholder
  at the same call sites — replace its body only). **Priority 2.**
- `dodo_client.py` — `create_collection()` for the Act I stratum-5 live
  receivable ($263,000, `CUST-4471`). **Priority 3.**

`agent/model.py`'s `call_fast()` / `call_strong()` (Tensormux routing) and
its call-count tracking already exist and are the **priority 4** cost-meter
integration — no new file needed there, just real API wiring.
