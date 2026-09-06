# reconFX

reconFX is an AI agent that finds out *why* a company's books don't add up — instead of just plugging the gap and moving on.

Finance teams end up with unexplained balances two ways: an old "clearing account" that quietly accumulated years of unresolved differences, and a current-month margin that doesn't match transfer-pricing policy. The normal fix in both cases is to shrug and force an accounting entry to make the number balance. reconFX instead runs an agent loop that reads the ledger, payroll, contracts, and policy documents, forms a hypothesis for each piece of the gap, checks it against real evidence, and either confirms it with a dollar amount and a disposition (reverse it, write it off, collect it, escalate it) or rejects it and moves on. It never invents a number — a deterministic Python engine owns all arithmetic; the LLM only reads documents and proposes/tests hypotheses.

It runs in two acts:
- **Act I — the excavation**: retrospectively decomposes a multi-year unexplained clearing-account balance into named, evidenced causes.
- **Act II — the live investigation**: prospectively explains a current-month margin deviation against transfer-pricing policy.

Sponsor integrations wired in: **Tensormux** (cost-aware model routing between a fast/cheap and a strong model), **Neatlogs** (full execution tracing, including rejected hypotheses), and **Dodo Payments** (a real hosted payment link for a genuine collectible receivable found during Act I).

## Requirements

- Python 3.11+
- Node.js (for the console UI)

## Setup

```bash
pip install -r requirements.txt
cd ui && npm install && cd ..
```

Copy `.env` and fill in whichever keys you have (all are optional — everything degrades to a deterministic stub if a key is missing or the API is unreachable):

```bash
TENSORMUX_API_KEY=
TENSORMUX_BASE_URL=
NEATLOGS_API_KEY=
DODO_API_KEY=
DODO_ENV=test
```

## Run it

**Just the agent, from the command line:**
```bash
python -m agent.act_one
python -m agent.act_two
```

**Full console (backend + UI):**
```bash
uvicorn api.main:app --reload --port 8000
```
in a second terminal:
```bash
cd ui && npm run dev
```
Open the Vite URL it prints, then trigger a run from the UI (or `POST /api/run/act-one` / `/api/run/act-two`) and watch the agent's reasoning stream in over the WebSocket.

## Tests

```bash
python -m pytest tests/ -q
```
