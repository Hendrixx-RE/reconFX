# Standalone console prototype

`reconfx-console.html` is a single-file, zero-dependency prototype of the controller's
workspace. Open it in a browser — no build, no server, no API key.

## What it is

A clickable working prototype of the **user-facing workflow**, built to show what a
controller actually sees and does:

- **My close queue** — the two items holding up the March close, with live decision counts
- **Clearing account 1900** — run the analysis, then action each of the six causes
- **March variance** — run the investigation, then sign off on the $5,000 residual
- **Activity** — every decision made this session, reversible

Every button changes state that persists across the session: acting on a finding updates
the tab badges, the progress bars, the remaining-unexplained figure, and the activity log,
and each action can be undone.

## What it is not

It does **not** talk to `api/` or the engine. All figures are hard-coded fixtures matching
the canonical numbers in `PLAN.md` §4, and the analysis runs are choreographed rather than
streamed from a real WebSocket. It is a UX prototype, not a client.

`ui/` (the Vite + React app) is the real client. This file exists to demonstrate and agree
the workflow and the language before that workflow is wired to live events — and as a
zero-risk fallback for recording the demo if the stack is unavailable.

## Language

Engine vocabulary (`test_hypothesis`, `TIMING_UNBILLED`, `BELOW_MATERIALITY`,
`recharge_flag`) is deliberately kept off the surface — it lives behind the
"Show the technical log" toggle inside each evidence popup. The visible copy is written
for a controller, not for the engine.
