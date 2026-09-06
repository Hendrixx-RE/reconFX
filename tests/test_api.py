"""Tests for FastAPI backend and WebSocket event stream (Phase 5)."""

import os
import time
import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.events import VALID_EVENT_TYPES, normalize_event, validate_event


@pytest.fixture
def client():
    return TestClient(app)


def test_status_endpoint(client):
    """GET /api/status returns ao_process_id, neatlogs_trace_url, dodo_test_link, and cost_summary."""
    resp = client.get("/api/status")
    assert resp.status_code == 200
    data = resp.json()

    assert "ao_process_id" in data
    assert "neatlogs_trace_url" in data
    assert "dodo_test_link" in data
    assert "cost_summary" in data

    cost = data["cost_summary"]
    assert isinstance(cost, dict)
    assert "fast_calls" in cost or "fast" in cost
    assert "strong_calls" in cost or "strong" in cost
    assert "formatted" in cost


def test_status_with_env_config(client, monkeypatch):
    """GET /api/status reflects configured environment variables."""
    monkeypatch.setenv("AO_PROCESS_ID", "test-ao-proc-123")
    monkeypatch.setenv("NEATLOGS_TRACE_URL", "https://app.neatlogs.com/traces/test-trace")

    from integrations import neatlogs_setup
    neatlogs_setup._trace_url = "https://app.neatlogs.com/traces/test-trace"

    resp = client.get("/api/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ao_process_id"] == "test-ao-proc-123"
    assert data["neatlogs_trace_url"] == "https://app.neatlogs.com/traces/test-trace"


def test_approve_endpoint(client):
    """POST /api/approve records controller decision and returns confirmation."""
    # Test APPROVE true-up
    payload = {
        "escalation_id": "ESC-2026-03-001",
        "decision": "APPROVE",
        "actor": "lead-controller",
    }
    resp = client.post("/api/approve", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "confirmed"
    assert data["decision"] == "APPROVE"
    assert data["decision_type"] == "APPROVE_TRUEUP"
    assert data["escalation_id"] == "ESC-2026-03-001"
    assert data["reference"] == "ESC-2026-03-001"
    assert data["actor"] == "lead-controller"

    # Test REJECT with entry_reference
    payload_reject = {
        "entry_reference": "JE-2026-03-TRUEUP",
        "decision": "REJECT",
    }
    resp_reject = client.post("/api/approve", json=payload_reject)
    assert resp_reject.status_code == 200
    data_reject = resp_reject.json()
    assert data_reject["status"] == "confirmed"
    assert data_reject["decision"] == "REJECT"
    assert data_reject["decision_type"] == "REJECT"
    assert data_reject["entry_reference"] == "JE-2026-03-TRUEUP"


def test_trigger_act_one_and_websocket_events(client):
    """WebSocket connection receives live events during a triggered act-one run."""
    with client.websocket_connect("/ws/events") as ws:
        # Trigger Act One run
        resp = client.post("/api/run/act-one")
        assert resp.status_code == 200
        run_data = resp.json()
        assert "run_id" in run_data
        assert run_data["status"] == "started"
        assert run_data["act"] == "EXCAVATION"

        # Collect streamed events
        received_events = []
        start_time = time.time()
        while time.time() - start_time < 5.0:
            try:
                event = ws.receive_json()
                received_events.append(event)
                # Act One ends with untraceable ESCALATION or COST
                if event.get("event_type") in ("ESCALATION", "COST"):
                    if any(e.get("event_type") == "FACTOR_ACCEPTED" for e in received_events):
                        break
            except Exception:
                break

        # Verification
        assert len(received_events) >= 1, "Expected at least one event over WebSocket"
        for ev in received_events:
            assert ev["event_type"] in VALID_EVENT_TYPES
            assert "act" in ev
            assert "timestamp" in ev
            assert "step" in ev
            assert "payload" in ev
            assert isinstance(ev["payload"], dict)

        event_types = [e["event_type"] for e in received_events]
        assert "TOOL_CALL" in event_types or "HYPOTHESIS" in event_types


def test_trigger_act_two(client):
    """POST /api/run/act-two triggers background investigation."""
    resp = client.post("/api/run/act-two", json={"entity_id": "ENT-IN-02", "period": "2026-03"})
    assert resp.status_code == 200
    data = resp.json()
    assert "run_id" in data
    assert data["status"] == "started"
    assert data["act"] == "INVESTIGATION"

    # Wait briefly for worker to register
    time.sleep(0.5)
    runs_resp = client.get("/api/runs")
    assert runs_resp.status_code == 200
    runs = runs_resp.json().get("runs", [])
    assert any(r["run_id"] == data["run_id"] for r in runs)


def test_event_normalization_and_validation():
    """Event schema correctly normalizes and validates Appendix B shapes."""
    raw = {
        "event_type": "TOOL_CALL",
        "act": "EXCAVATION",
        "step": 1,
        "payload": {
            "tool_name": "query_clearing_account",
            "kwargs": {"account": "1900"},
            "result": {"items": [1, 2, 3]},
        },
    }
    normalized = normalize_event(raw)
    assert normalized["event_type"] == "TOOL_CALL"
    assert normalized["act"] == "EXCAVATION"
    assert normalized["step"] == 1
    assert "timestamp" in normalized

    model_obj = validate_event(raw)
    assert model_obj.event_type == "TOOL_CALL"

    # Aliased decision type normalization
    alias_raw = {
        "event_type": "APPROVE_COLLECTION",
        "act": "EXCAVATION",
        "step": 5,
        "payload": {"payment_id": "pay_123"},
    }
    norm_alias = normalize_event(alias_raw)
    assert norm_alias["event_type"] == "DECISION"
    assert norm_alias["payload"]["decision_type"] == "APPROVE_COLLECTION"
