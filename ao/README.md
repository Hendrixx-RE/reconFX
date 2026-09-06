# ao/ — Phase 4: Agent Orchestrator ledger

**Status: not started.**

Per PLAN.md §6.1, this holds the immutable audit ledger deployed to a local
`aos` process:

- `reconfx_ledger.lua` — Lua process exposing `RecordStep`, `RecordDecision`,
  `GetLedger` handlers (see PLAN.md §6.1 for the full source).

`integrations/ao_client.py` is the Python-side dispatcher that sends
messages here from `agent/loop.py`. Every accepted/rejected factor and
every controller decision must become a message to this process —
PLAN.md calls this the mandatory, load-bearing sponsor integration.
**Never cut this**, per the Phase 4 cut list.
