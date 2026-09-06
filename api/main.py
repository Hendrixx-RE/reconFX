"""FastAPI + WebSocket console backend for reconFX (README.md §5.3, §7 Phase 5).

Endpoints:
  WS  /ws/events         Streams state events live (Appendix B schema) as Act I / II execute.
  POST /api/run/act-one   Triggers Act I excavation in background, returns run_id immediately.
  POST /api/run/act-two   Triggers Act II investigation in background, returns run_id immediately.
  GET  /api/status        Returns { neatlogs_trace_url, dodo_test_link, cost_summary }.
  POST /api/approve       Records controller decision and broadcasts a DECISION event.
  GET  /api/events        Returns buffered event history.
  GET  /api/runs/{run_id} Returns status and results of a run.
"""

import asyncio
import json
import logging
import os
import threading
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agent import model
from agent.act_one import run_act_one
from agent.act_two import run_act_two
from api.events import (
    build_cost_event,
    build_decision_event,
    normalize_event,
    sanitize_value,
)
from integrations import dodo_client, neatlogs_setup

logger = logging.getLogger("api.main")
logging.basicConfig(level=logging.INFO)


class ConnectionManager:
    """Manages active WebSocket connections and thread-safe event broadcast."""

    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self._lock = threading.Lock()
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        with self._lock:
            self.active_connections.append(websocket)
        logger.info("WebSocket connected. Active clients: %d", len(self.active_connections))

    def disconnect(self, websocket: WebSocket) -> None:
        with self._lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
        logger.info("WebSocket disconnected. Active clients: %d", len(self.active_connections))

    def broadcast(self, event: Dict[str, Any]) -> None:
        """Broadcasts an event dict to all connected WebSocket clients safely."""
        with self._lock:
            conns = list(self.active_connections)

        if not conns:
            return

        text = json.dumps(event, default=str)

        async def _send_all() -> None:
            dead: List[WebSocket] = []
            for ws in conns:
                try:
                    await ws.send_text(text)
                except Exception:
                    dead.append(ws)
            if dead:
                with self._lock:
                    for d in dead:
                        if d in self.active_connections:
                            self.active_connections.remove(d)

        loop = self._loop
        if loop is None or loop.is_closed():
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

        if loop and loop.is_running():
            try:
                running = None
                try:
                    running = asyncio.get_running_loop()
                except RuntimeError:
                    pass

                if running == loop:
                    asyncio.create_task(_send_all())
                else:
                    asyncio.run_coroutine_threadsafe(_send_all(), loop)
            except Exception as exc:
                logger.debug("Failed to schedule broadcast on event loop: %s", exc)


manager = ConnectionManager()

# In-memory storage for runs, event logs, and status caching
_runs_lock = threading.Lock()
_runs: Dict[str, Dict[str, Any]] = {}
_event_store: List[Dict[str, Any]] = []
_state: Dict[str, Any] = {
    "last_dodo_link": None,
    "last_dodo_collection": None,
}


def get_dodo_test_link() -> Optional[str]:
    """Resolves the last test link from Dodo Payments client."""
    if _state.get("last_dodo_link"):
        return _state["last_dodo_link"]

    # Check if dodo_client exposes a helper
    if hasattr(dodo_client, "get_last_payment_link") and callable(getattr(dodo_client, "get_last_payment_link")):
        try:
            link = dodo_client.get_last_payment_link()
            if link:
                _state["last_dodo_link"] = str(link)
                return _state["last_dodo_link"]
        except Exception as exc:
            logger.debug("Error calling get_last_payment_link: %s", exc)

    # Fallback to create_payment_link (stub or live mode per §6.3)
    try:
        col = dodo_client.create_payment_link(
            customer_ref="CUST-4471",
            amount_usd=263000.00,
            description="Reinstated customer receivable (CUST-4471)",
        )
        if isinstance(col, dict):
            link = col.get("payment_link") or col.get("checkout_url")
            _state["last_dodo_link"] = str(link) if link else None
            _state["last_dodo_collection"] = col
            return _state["last_dodo_link"]
        elif isinstance(col, str):
            _state["last_dodo_link"] = col
            return col
    except Exception as exc:
        logger.warning("Error generating initial Dodo test link: %s", exc)

    return None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager to capture asyncio event loop and init integrations."""
    manager.set_loop(asyncio.get_running_loop())
    try:
        neatlogs_setup.init_neatlogs()
    except Exception as exc:
        logger.debug("Neatlogs init on startup skipped/failed: %s", exc)
    yield


app = FastAPI(
    title="reconFX Console Backend",
    description="FastAPI + WebSocket backend for forensic reconciliation agent",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS enabled for local Vite / frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -----------------------------------------------------------------------------
# Request / Response Models
# -----------------------------------------------------------------------------

class RunActOneRequest(BaseModel):
    model_config = {"extra": "allow"}


class RunActTwoRequest(BaseModel):
    model_config = {"extra": "allow"}
    entity_id: str = "ENT-IN-02"
    period: str = "2026-03"


class ApproveRequest(BaseModel):
    model_config = {"extra": "allow"}
    escalation_id: Optional[str] = None
    entry_reference: Optional[str] = None
    decision: str = "APPROVE"  # "APPROVE" | "REJECT"
    actor: str = "controller"
    decision_type: Optional[str] = None
    notes: Optional[str] = None


# -----------------------------------------------------------------------------
# Background Workers
# -----------------------------------------------------------------------------

def _run_act_one_worker(run_id: str) -> None:
    with _runs_lock:
        if run_id in _runs:
            _runs[run_id]["status"] = "running"

    try:
        def on_event(raw_event: Dict[str, Any]) -> None:
            try:
                norm = normalize_event(raw_event)
            except Exception as exc:
                logger.warning("Event normalization error: %s", exc)
                norm = raw_event

            # Track dodo link if emitted in stratum 5
            payload = norm.get("payload", {})
            if isinstance(payload, dict) and payload.get("payment_link"):
                _state["last_dodo_link"] = payload.get("payment_link")
                _state["last_dodo_collection"] = payload

            _event_store.append(norm)
            with _runs_lock:
                if run_id in _runs:
                    _runs[run_id]["events"].append(norm)

            # Broadcast over WebSocket
            manager.broadcast(norm)

        result = run_act_one(on_event=on_event)

        # Emit completion COST event
        try:
            cost_summary = model.get_cost_summary()
            cost_event = build_cost_event(
                cost_summary=cost_summary,
                act="EXCAVATION",
                step=len(_runs[run_id]["events"]),
            )
            on_event(cost_event)
        except Exception as exc:
            logger.debug("Failed emitting cost event: %s", exc)

        with _runs_lock:
            if run_id in _runs:
                _runs[run_id]["status"] = "completed"
                _runs[run_id]["result"] = sanitize_value(result)
                _runs[run_id]["end_time"] = datetime.now(timezone.utc).isoformat()
    except Exception as exc:
        logger.exception("Act One run %s failed: %s", run_id, exc)
        with _runs_lock:
            if run_id in _runs:
                _runs[run_id]["status"] = "failed"
                _runs[run_id]["error"] = str(exc)
                _runs[run_id]["end_time"] = datetime.now(timezone.utc).isoformat()


def _run_act_two_worker(run_id: str, entity_id: str, period: str) -> None:
    with _runs_lock:
        if run_id in _runs:
            _runs[run_id]["status"] = "running"

    try:
        def on_event(raw_event: Dict[str, Any]) -> None:
            try:
                norm = normalize_event(raw_event)
            except Exception as exc:
                logger.warning("Event normalization error: %s", exc)
                norm = raw_event

            _event_store.append(norm)
            with _runs_lock:
                if run_id in _runs:
                    _runs[run_id]["events"].append(norm)

            # Broadcast over WebSocket
            manager.broadcast(norm)

        result = run_act_two(entity_id=entity_id, period=period, on_event=on_event)

        # Emit completion COST event
        try:
            cost_summary = model.get_cost_summary()
            cost_event = build_cost_event(
                cost_summary=cost_summary,
                act="INVESTIGATION",
                step=len(_runs[run_id]["events"]),
            )
            on_event(cost_event)
        except Exception as exc:
            logger.debug("Failed emitting cost event: %s", exc)

        with _runs_lock:
            if run_id in _runs:
                _runs[run_id]["status"] = "completed"
                _runs[run_id]["result"] = sanitize_value(result)
                _runs[run_id]["end_time"] = datetime.now(timezone.utc).isoformat()
    except Exception as exc:
        logger.exception("Act Two run %s failed: %s", run_id, exc)
        with _runs_lock:
            if run_id in _runs:
                _runs[run_id]["status"] = "failed"
                _runs[run_id]["error"] = str(exc)
                _runs[run_id]["end_time"] = datetime.now(timezone.utc).isoformat()


# -----------------------------------------------------------------------------
# Endpoints
# -----------------------------------------------------------------------------

@app.websocket("/ws/events")
async def websocket_events(websocket: WebSocket):
    """WebSocket endpoint streaming live state events (Appendix B schema)."""
    manager.set_loop(asyncio.get_running_loop())
    await manager.connect(websocket)
    try:
        while True:
            msg = await websocket.receive_text()
            if msg.strip() == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)


@app.post("/api/run/act-one")
async def trigger_act_one(req: Optional[RunActOneRequest] = None):
    """Trigger Act I excavation in the background. Return immediately with run ID."""
    run_id = f"act-one-{uuid.uuid4().hex[:8]}"
    with _runs_lock:
        _runs[run_id] = {
            "run_id": run_id,
            "act": "EXCAVATION",
            "status": "pending",
            "start_time": datetime.now(timezone.utc).isoformat(),
            "end_time": None,
            "events": [],
            "result": None,
            "error": None,
        }

    thread = threading.Thread(
        target=_run_act_one_worker,
        args=(run_id,),
        daemon=True,
        name=f"worker-{run_id}",
    )
    thread.start()

    return {
        "run_id": run_id,
        "status": "started",
        "act": "EXCAVATION",
    }


@app.post("/api/run/act-two")
async def trigger_act_two(req: Optional[RunActTwoRequest] = None):
    """Trigger Act II investigation in the background. Return immediately with run ID."""
    entity_id = req.entity_id if req and req.entity_id else "ENT-IN-02"
    period = req.period if req and req.period else "2026-03"
    run_id = f"act-two-{uuid.uuid4().hex[:8]}"

    with _runs_lock:
        _runs[run_id] = {
            "run_id": run_id,
            "act": "INVESTIGATION",
            "entity_id": entity_id,
            "period": period,
            "status": "pending",
            "start_time": datetime.now(timezone.utc).isoformat(),
            "end_time": None,
            "events": [],
            "result": None,
            "error": None,
        }

    thread = threading.Thread(
        target=_run_act_two_worker,
        args=(run_id, entity_id, period),
        daemon=True,
        name=f"worker-{run_id}",
    )
    thread.start()

    return {
        "run_id": run_id,
        "status": "started",
        "act": "INVESTIGATION",
        "entity_id": entity_id,
        "period": period,
    }


@app.get("/api/status")
async def get_status():
    """Returns active system status: Neatlogs trace URL, Dodo test link, cost summary."""
    neatlogs_url = neatlogs_setup.get_trace_url()
    dodo_link = get_dodo_test_link()
    cost_summary = model.get_cost_summary()

    return {
        "neatlogs_trace_url": neatlogs_url,
        "dodo_test_link": dodo_link,
        "cost_summary": cost_summary,
    }


@app.post("/api/approve")
async def approve(req: ApproveRequest):
    """Records a controller decision (APPROVE | REJECT) and broadcasts a DECISION event."""
    decision_raw = (req.decision or "APPROVE").strip().upper()

    if req.decision_type:
        dt = req.decision_type.strip().upper()
    elif decision_raw in ("APPROVE", "APPROVE_TRUEUP", "APPROVED"):
        dt = "APPROVE_TRUEUP"
    elif decision_raw in ("APPROVE_COLLECTION",):
        dt = "APPROVE_COLLECTION"
    elif decision_raw in ("REJECT", "REJECTED"):
        dt = "REJECT"
    else:
        dt = decision_raw

    ref = req.escalation_id or req.entry_reference or "CONTROLLER_REVIEW"
    actor = req.actor or "controller"

    # Broadcast DECISION event
    decision_event = build_decision_event(
        decision_type=dt,
        actor=actor,
        reference=ref,
        act="INVESTIGATION",
        step=len(_event_store),
        decision=req.decision,
        escalation_id=req.escalation_id,
        entry_reference=req.entry_reference,
    )
    _event_store.append(decision_event)
    manager.broadcast(decision_event)

    return {
        "status": "confirmed",
        "decision": req.decision,
        "decision_type": dt,
        "reference": ref,
        "escalation_id": req.escalation_id,
        "entry_reference": req.entry_reference,
        "actor": actor,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/events")
async def get_events(limit: int = 200, act: Optional[str] = None):
    """Return buffered event history, optionally filtered by act."""
    events = _event_store
    if act:
        events = [e for e in events if e.get("act", "").upper() == act.upper()]
    return {
        "count": len(events[-limit:]),
        "total": len(events),
        "events": events[-limit:],
    }


@app.get("/api/runs")
async def list_runs():
    """List all tracked runs."""
    with _runs_lock:
        runs_summary = [
            {
                "run_id": r["run_id"],
                "act": r["act"],
                "status": r["status"],
                "start_time": r["start_time"],
                "end_time": r["end_time"],
                "event_count": len(r.get("events", [])),
                "error": r.get("error"),
            }
            for r in _runs.values()
        ]
    return {"runs": runs_summary}


@app.get("/api/runs/{run_id}")
async def get_run_details(run_id: str):
    """Get details and results for a specific run."""
    with _runs_lock:
        run_data = _runs.get(run_id)
    if not run_data:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    return run_data


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    uvicorn.run("api.main:app", host=host, port=port, reload=False)
