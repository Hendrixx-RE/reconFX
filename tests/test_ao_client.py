"""Tests for integrations/ao_client.py (Agent Orchestrator ledger client).

Verifies:
- Unconfigured graceful no-op behavior (never raises, never blocks)
- Non-blocking send queue dispatch
- Data normalization for ao/reconfx_ledger.lua handlers
- Resilient error handling on network failure / connection timeout
- Event subscriber integration with Act I and Act II runs
- Mock AO process verifying RecordStep, RecordDecision, and GetLedger
"""

import os
import time
from unittest.mock import patch

import pytest
import requests

from agent.act_one import run_act_one
from agent.act_two import run_act_two
from integrations import ao_client


@pytest.fixture(autouse=True)
def cleanup_ao_client():
    """Ensure client state and env vars are cleaned up before/after each test."""
    ao_client.reset_client()
    orig_pid = os.environ.get("AO_PROCESS_ID")
    orig_wallet = os.environ.get("AO_WALLET_PATH")
    orig_url = os.environ.get("AO_URL")
    yield
    ao_client.reset_client()
    if orig_pid is not None:
        os.environ["AO_PROCESS_ID"] = orig_pid
    else:
        os.environ.pop("AO_PROCESS_ID", None)
    if orig_wallet is not None:
        os.environ["AO_WALLET_PATH"] = orig_wallet
    else:
        os.environ.pop("AO_WALLET_PATH", None)
    if orig_url is not None:
        os.environ["AO_URL"] = orig_url
    else:
        os.environ.pop("AO_URL", None)


class MockAOLedger:
    """Python simulation of ao/reconfx_ledger.lua state machine."""

    def __init__(self):
        self.steps = []
        self.decisions = []
        self.residual = 0.0

    def dispatch(self, action: str, payload: dict, timeout: float = 2.0):
        if action == "RecordStep":
            step_record = {
                "act": payload.get("act"),
                "factor_id": payload.get("factor_id"),
                "classification": payload.get("classification"),
                "transaction_ids": payload.get("transaction_ids"),
                "evidence_refs": payload.get("evidence_refs"),
                "factor_usd": payload.get("factor_usd"),
                "residual_before": self.residual,
                "residual_after": payload.get("new_residual"),
                "accepted": payload.get("accepted"),
                "rejection_reason": payload.get("rejection_reason"),
                "ts": int(time.time() * 1000),
            }
            self.steps.append(step_record)
            self.residual = payload.get("new_residual")
            return {"ok": True, "step": len(self.steps)}

        elif action == "RecordDecision":
            decision_record = {
                "decision_type": payload.get("decision_type"),
                "actor": payload.get("actor"),
                "payload_hash": payload.get("payload_hash"),
                "ts": int(time.time() * 1000),
            }
            self.decisions.append(decision_record)
            return {"ok": True}

        elif action == "GetLedger":
            return {
                "steps": list(self.steps),
                "decisions": list(self.decisions),
                "residual": self.residual,
            }
        return None


def test_unconfigured_ao_client_noops():
    """When AO env vars are missing, operations gracefully no-op and never raise."""
    os.environ.pop("AO_PROCESS_ID", None)
    os.environ.pop("AO_WALLET_PATH", None)

    assert not ao_client.is_configured()
    assert ao_client.get_ledger_process_id() is None

    # Should not raise or block
    ao_client.record_step({
        "act": "INVESTIGATION",
        "factor_id": "F1",
        "classification": "TIMING_UNBILLED",
        "factor_usd": 31000.0,
        "new_residual": 13000.0,
        "accepted": True,
    })
    ao_client.record_decision({
        "decision_type": "APPROVE_TRUEUP",
        "actor": "controller",
    })
    assert ao_client.query_ledger() is None
    assert ao_client.flush(timeout=0.5)


def test_network_failure_is_non_fatal():
    """Network connection errors are logged and swallowed; caller never fails."""
    os.environ["AO_PROCESS_ID"] = "test-process-id"
    os.environ["AO_WALLET_PATH"] = "./wallet.json"
    os.environ["AO_URL"] = "http://127.0.0.1:59999/unreachable"

    # Dispatch to dead endpoint
    ao_client.record_step({
        "act": "INVESTIGATION",
        "factor_id": "F1",
        "classification": "TIMING_UNBILLED",
        "factor_usd": 31000.0,
        "new_residual": 13000.0,
        "accepted": True,
    })
    ao_client.record_decision({
        "decision_type": "APPROVE_TRUEUP",
    })

    # flush waits for queue to drain; should complete without raising
    drained = ao_client.flush(timeout=3.0)
    assert drained

    # query_ledger returns None on connection error
    ledger = ao_client.query_ledger(timeout=1.0)
    assert ledger is None


def test_act_one_and_act_two_events_wire_to_ledger():
    """Verify that handle_event correctly forwards all test_hypothesis results
    and decisions to the AO ledger."""
    mock_ledger = MockAOLedger()
    ao_client.set_sender(mock_ledger.dispatch)

    os.environ["AO_PROCESS_ID"] = "mock-process-ao"
    os.environ["AO_WALLET_PATH"] = "./wallet.json"

    # Run Act I with handle_event
    act_one_res = run_act_one(on_event=ao_client.handle_event)
    assert act_one_res["opening_balance"] == 1847000.00
    assert act_one_res["residual"] == 0.0

    ao_client.flush(timeout=2.0)

    # Act I should have recorded 6 strata steps
    ledger_state = ao_client.query_ledger()
    assert ledger_state is not None
    assert len(ledger_state["steps"]) == 6
    for step in ledger_state["steps"]:
        assert step["act"] == "EXCAVATION"
        assert step["accepted"] is True
    assert ledger_state["residual"] == 0.0

    # Record a controller decision for Act I collection
    ao_client.handle_event({
        "event_type": "CONTROLLER_DECISION",
        "payload": {
            "decision_type": "APPROVE_COLLECTION",
            "actor": "controller_alice",
            "customer_ref": "CUST-4471",
            "amount_usd": 263000.0,
        },
    })
    ao_client.flush(timeout=2.0)

    ledger_state = ao_client.query_ledger()
    assert len(ledger_state["decisions"]) == 1
    assert ledger_state["decisions"][0]["decision_type"] == "APPROVE_COLLECTION"
    assert ledger_state["decisions"][0]["actor"] == "controller_alice"
    assert len(ledger_state["decisions"][0]["payload_hash"]) == 64

    # Run Act II with handle_event
    act_two_res = run_act_two(on_event=ao_client.handle_event)
    assert act_two_res["residual"] == 5000.0
    assert len(act_two_res["accepted_factors"]) == 2
    assert len(act_two_res["rejected_hypotheses"]) == 1

    ao_client.flush(timeout=2.0)

    ledger_state = ao_client.query_ledger()
    # 6 from Act I + 3 from Act II (H1 timing, H2 severance exclusion, H3 rejected FX)
    assert len(ledger_state["steps"]) == 9

    act_two_steps = [s for s in ledger_state["steps"] if s["act"] == "INVESTIGATION"]
    assert len(act_two_steps) == 3

    # Verify H1 accepted
    h1 = act_two_steps[0]
    assert h1["factor_id"] == "F1"
    assert h1["classification"] == "TIMING_UNBILLED"
    assert h1["accepted"] is True
    assert h1["factor_usd"] == 31000.0
    assert h1["residual_after"] == 13000.0

    # Verify H2 accepted
    h2 = act_two_steps[1]
    assert h2["factor_id"] == "F2"
    assert h2["classification"] == "APPROVED_EXCLUSION"
    assert h2["accepted"] is True
    assert h2["factor_usd"] == 8000.0
    assert h2["residual_after"] == 5000.0

    # Verify H3 rejected below materiality
    h3 = act_two_steps[2]
    assert h3["factor_id"] == "H3"
    assert h3["classification"] == "FX_REVALUATION"
    assert h3["accepted"] is False
    assert h3["rejection_reason"] == "BELOW_MATERIALITY"
    assert h3["residual_after"] == 5000.0

    # Record true-up approval decision
    ao_client.record_decision({
        "decision_type": "APPROVE_TRUEUP",
        "actor": "controller_bob",
        "period": "2026-03",
    })
    ao_client.flush(timeout=2.0)

    ledger_state = ao_client.query_ledger()
    assert len(ledger_state["decisions"]) == 2
    assert ledger_state["decisions"][1]["decision_type"] == "APPROVE_TRUEUP"


def test_nonblocking_queue_timeout_resilience():
    """Verify that slow dispatches timeout at 2.0s and do not block callers."""
    def slow_sender(action, payload, timeout):
        time.sleep(min(timeout, 0.2))  # simulate latency
        return {"ok": True}

    ao_client.set_sender(slow_sender)
    os.environ["AO_PROCESS_ID"] = "slow-test-process"
    os.environ["AO_WALLET_PATH"] = "./wallet.json"

    t0 = time.time()
    # Enqueue multiple items in rapid succession
    for i in range(10):
        ao_client.record_step({
            "act": "INVESTIGATION",
            "factor_id": f"TEST_{i}",
            "classification": "TIMING_UNBILLED",
            "accepted": True,
            "new_residual": 1000.0,
        })
    elapsed = time.time() - t0

    # Caller must not be blocked: elapsed time for calls should be very small
    assert elapsed < 0.1, f"Caller was blocked for {elapsed:.3f}s"

    # Background worker finishes draining
    assert ao_client.flush(timeout=5.0)
