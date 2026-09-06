# reconFX — Build status

Single source of truth is the repository root (`agent/`, `engine/`,
`data/`, `tests/`). A duplicate, incompatible implementation previously
lived at `reconfx/` (from the `phase1-*` branches, nested under a
misread of README.md §5.3's tree diagram) — it has been removed; nothing
from it was more complete than what's here.

## Phase 1 — Evidence corpus: **mostly done**

- `data/` has all required files, internally consistent, sums reconcile
  to every canonical README.md §4 number.
- **Known gap:** `payroll_register.csv` only carries the current period
  (2026-03). README.md requires 7 of the 11 `IC margin plug` months
  (2024-06 → 2025-04) to correlate with a post-cutoff payroll posting —
  those historical rows haven't been added yet by anyone. This is why
  `tests/test_canonical_numbers.py::test_plug_months_correlate_with_late_payroll`
  is `xfail` rather than passing.

## Phase 2 — Deterministic engine: **done**

- `engine/baseline.py` computes the Act II baseline from source files
  (never hardcoded).
- `engine/decomposition.py` enforces exclusivity, the materiality gate,
  and rejects over-attribution (residual never goes negative).
- `engine/dispositions.py`, `engine/journal.py` — classification routing
  and balance-asserting JE construction.

## Phase 3 — Agent layer: **done**

- `agent/tools.py` — all 7 tools per §5.2.
- `agent/loop.py` — ReAct loop, `MAX_STEPS=12`, retry-once-then-escalate
  on malformed tool calls, event emission.
- `agent/act_one.py` / `agent/act_two.py` — both acts run end to end and
  reproduce every canonical §4 number exactly.
- `agent/model.py` — Tensormux client stub (real wiring is Phase 4).

## Phase 4 — Sponsor integrations: **not started**

Placeholders at `ao/`, `api/`, `integrations/` describe exactly what
goes where. See each folder's README.

## Phase 5 — Controller console: **not started**

Placeholder at `ui/`. See its README.

## Phase 6 — Hardening, dry runs, capture: **not started**

Depends on Phase 4/5 existing first.

## Running the tests

```
pip install -r requirements.txt
pytest tests/ -v
```

Expect **17 passed, 1 xfail** (the payroll-correlation gap above).
