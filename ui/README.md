# ui/ — Phase 5: Controller console

**Status: not started.**

Per PLAN.md §5.3/§5, a React + Vite console consuming the WebSocket event
stream from `api/`. One screen, two panels — no browser-side computation,
every number arrives from the backend.

Expected under `src/components/`:
`TraceStream.jsx`, `StrataColumn.jsx`, `ResidualWaterfall.jsx`,
`EvidenceCard.jsx`, `ApprovalModal.jsx` (never cut — it's the
human-judgment criterion made visible), `CostMeter.jsx`.
