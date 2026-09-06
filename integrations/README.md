# integrations/ — Phase 4: sponsor integrations

**Status: implemented.** Each client wraps its sponsor stack in a way a judge
can independently verify on screen, and each degrades gracefully (never
blocks the demo) if the network or the sponsor's API is unavailable:

- `ao_client.py` — non-blocking send queue to the AO ledger (`ao/`),
  2-second timeout. **Priority 1, mandatory.**
- `neatlogs_setup.py` — `neatlogs.init()` plus span decorators on the 7
  tools in `agent/tools.py` (real `neatlogs.span(kind=...)` swapped in when
  `neatlogs` is installed and `NEATLOGS_API_KEY` is set; falls back to a
  no-op wrapper otherwise). **Priority 2.**
- `dodo_client.py` — `create_collection()` for the Act I stratum-5 live
  receivable ($263,000, `CUST-4471`); hits Dodo's Checkout Sessions API
  (`POST /checkouts`) against `test.dodopayments.com` / `live.dodopayments.com`.
  **Priority 3.**

`agent/model.py`'s `call_fast()` / `call_strong()` route through the
Tensormux gateway's OpenAI-compatible `/v1/chat/completions` endpoint when
`TENSORMUX_API_KEY` / `TENSORMUX_BASE_URL` are configured, and track call
counts for the console cost meter. **Priority 4.**

All four fall back to deterministic stub responses (never raise, never
block) when the corresponding env vars are absent or the sponsor API is
unreachable — see each module's docstring for the exact fallback behavior.
