# api/ — Phase 4/5: FastAPI + WebSocket layer

**Status: not started.**

Per PLAN.md §5.3, this is the boundary between `agent/` and `ui/`:

- `main.py` — FastAPI app, WebSocket endpoint streaming state events
  (Appendix B schema) to the console as `agent/loop.py` emits them via its
  `on_event` callback.
- `events.py` — the event schema itself (`TOOL_CALL`, `HYPOTHESIS`,
  `FACTOR_ACCEPTED`, `FACTOR_REJECTED`, `RECOVERY_FOUND`, `DISPOSITION`,
  `ESCALATION`, `DECISION`, `COST`).

`agent/loop.py`'s `on_event` callback is already the exact seam this layer
needs to subscribe to — no changes to `agent/` should be required to wire
this up.
