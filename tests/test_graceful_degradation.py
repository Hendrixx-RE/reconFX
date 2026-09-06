"""Tests for graceful degradation of integrations (README.md §7 Phase 6).

Verifies that for each integration (AO, Neatlogs, Dodo, Tensormux, and Voice Briefing):
1. When unconfigured (env vars unset), operations degrade gracefully without crashing.
2. When configured but unreachable / raising errors, failures are logged and non-fatal.
3. run_act_one() and run_act_two() complete with the exact canonical numbers from README §4.
4. With all integrations disabled or network offline, both acts still complete.
5. Replay fixture produces byte-identical canonical numbers with zero network dependency.
"""

import os
import socket
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
import requests

from agent import model
from agent.act_one import run_act_one
from agent.act_two import run_act_two
from integrations import ao_client, dodo_client, neatlogs_setup, voice_client


# Canonical numbers per README §4
CANONICAL_ACT_ONE_OPENING = Decimal("1847000.00")
CANONICAL_ACT_ONE_RESIDUAL = Decimal("0.000")
CANONICAL_ACT_ONE_STRATA_SUM = Decimal("1847000.00")

CANONICAL_ACT_TWO_DEVIATION = Decimal("44000.00")
CANONICAL_ACT_TWO_RESIDUAL = Decimal("5000.000")
CANONICAL_ACT_TWO_F1_TIMING = Decimal("31000.000")
CANONICAL_ACT_TWO_F2_EXCLUSION = Decimal("8000.000")
CANONICAL_ACT_TWO_H3_FX_IMPACT = Decimal("340.000")
CANONICAL_ACT_TWO_RECOVERY = Decimal("14000.000")


def _assert_canonical_act_one(result: dict) -> None:
    """Assert Act I results match README §4 canonical figures."""
    assert result["opening_balance"] == CANONICAL_ACT_ONE_OPENING
    assert result["residual"] == CANONICAL_ACT_ONE_RESIDUAL
    assert len(result["strata"]) == 6

    strata_sum = sum(Decimal(s["factor_usd"]) for s in result["strata"])
    assert strata_sum == CANONICAL_ACT_ONE_STRATA_SUM

    strata_by_class = {s["classification"]: Decimal(s["factor_usd"]) for s in result["strata"]}
    assert strata_by_class["ERP_CUTOVER_ARTIFACT"] == Decimal("612000.000")
    assert strata_by_class["UNREVERSED_FX_REVALUATION"] == Decimal("384000.000")
    assert strata_by_class["DUPLICATE_AP_VENDOR_FEED"] == Decimal("206000.000")
    assert strata_by_class["ACCRUED_MARGIN_PLUG"] == Decimal("290000.000")
    assert strata_by_class["LIVE_COLLECTIBLE_RECEIVABLE"] == Decimal("263000.000")
    assert strata_by_class["UNTRACEABLE"] == Decimal("92000.000")

    assert result["escalation"] is not None
    assert result["escalation"]["reason"] == "UNTRACEABLE_CLEARING_BALANCE"


def _assert_canonical_act_two(result: dict) -> None:
    """Assert Act II results match README §4 canonical figures."""
    assert result["residual"] == CANONICAL_ACT_TWO_RESIDUAL
    assert len(result["accepted_factors"]) == 2
    assert Decimal(result["accepted_factors"][0]["factor_usd"]) == CANONICAL_ACT_TWO_F1_TIMING
    assert Decimal(result["accepted_factors"][1]["factor_usd"]) == CANONICAL_ACT_TWO_F2_EXCLUSION

    total_explained = sum(Decimal(f["factor_usd"]) for f in result["accepted_factors"])
    assert total_explained + result["residual"] == CANONICAL_ACT_TWO_DEVIATION

    assert len(result["rejected_hypotheses"]) == 1
    assert result["rejected_hypotheses"][0]["hypothesis"] == "FX_REVALUATION"
    assert Decimal(result["rejected_hypotheses"][0]["computed_impact_usd"]) == CANONICAL_ACT_TWO_H3_FX_IMPACT
    assert result["rejected_hypotheses"][0]["rejection_reason"] == "BELOW_MATERIALITY"

    assert len(result["recovery_findings"]) == 1
    assert Decimal(result["recovery_findings"][0]["entitlement_impact_usd"]) == CANONICAL_ACT_TWO_RECOVERY

    assert result["escalation"] is not None
    assert result["escalation"]["reason"] == "RESIDUAL_UNEXPLAINED"


@pytest.fixture(autouse=True)
def reset_integrations():
    """Clean up integration state and env vars before and after each test."""
    ao_client.reset_client()
    model.reset_call_counts()
    neatlogs_setup._trace_url = None
    neatlogs_setup._initialized = False
    orig_env = dict(os.environ)
    yield
    ao_client.reset_client()
    model.reset_call_counts()
    neatlogs_setup._trace_url = None
    neatlogs_setup._initialized = False
    os.environ.clear()
    os.environ.update(orig_env)


# ===========================================================================
# 1. Agent Orchestrator (AO) degradation
# ===========================================================================

def test_ao_unconfigured():
    """AO client unconfigured -> no-ops cleanly, both acts complete with canonical numbers."""
    os.environ.pop("AO_PROCESS_ID", None)
    os.environ.pop("AO_WALLET_PATH", None)
    assert not ao_client.is_configured()

    r1 = run_act_one(on_event=ao_client.handle_event)
    _assert_canonical_act_one(r1)

    r2 = run_act_two(on_event=ao_client.handle_event)
    _assert_canonical_act_two(r2)


def test_ao_unreachable_network_error(monkeypatch):
    """AO configured but HTTP endpoint unreachable -> logs warning, non-fatal."""
    os.environ["AO_PROCESS_ID"] = "proc_test_123"
    os.environ["AO_WALLET_PATH"] = "/fake/wallet.json"
    os.environ["AO_URL"] = "http://localhost:6363"

    def mock_post(*args, **kwargs):
        raise requests.ConnectionError("Failed to connect to AO process at localhost:6363")

    monkeypatch.setattr(requests, "post", mock_post)

    r1 = run_act_one(on_event=ao_client.handle_event)
    _assert_canonical_act_one(r1)

    r2 = run_act_two(on_event=ao_client.handle_event)
    _assert_canonical_act_two(r2)


def test_ao_dispatch_raises(monkeypatch):
    """AO dispatcher raises unexpected exception -> handle_event catches and logs."""
    os.environ["AO_PROCESS_ID"] = "proc_test_123"
    os.environ["AO_WALLET_PATH"] = "/fake/wallet.json"

    def exploding_sender(*args, **kwargs):
        raise RuntimeError("AO ledger process internal panic")

    ao_client.set_sender(exploding_sender)

    r1 = run_act_one(on_event=ao_client.handle_event)
    _assert_canonical_act_one(r1)

    r2 = run_act_two(on_event=ao_client.handle_event)
    _assert_canonical_act_two(r2)


# ===========================================================================
# 2. Neatlogs degradation
# ===========================================================================

def test_neatlogs_unconfigured():
    """Neatlogs API key unset -> tracing skipped, canonical numbers untouched."""
    os.environ.pop("NEATLOGS_API_KEY", None)
    assert neatlogs_setup.get_trace_url() is None

    r1 = run_act_one()
    _assert_canonical_act_one(r1)

    r2 = run_act_two()
    _assert_canonical_act_two(r2)


def test_neatlogs_init_fails(monkeypatch):
    """Neatlogs initialization raises -> graceful fallback to untraced execution."""
    os.environ["NEATLOGS_API_KEY"] = "fake_neatlogs_key"

    def exploding_init(*args, **kwargs):
        raise RuntimeError("Neatlogs API rate limit / 500 error")

    monkeypatch.setattr(neatlogs_setup, "init_neatlogs", exploding_init)

    r1 = run_act_one()
    _assert_canonical_act_one(r1)

    r2 = run_act_two()
    _assert_canonical_act_two(r2)


def test_neatlogs_span_fails(monkeypatch):
    """Neatlogs span wrapper throws error -> underlying tools still execute cleanly."""
    os.environ["NEATLOGS_API_KEY"] = "fake_neatlogs_key"

    try:
        import neatlogs
        def exploding_span(*args, **kwargs):
            raise RuntimeError("Neatlogs span failure")
        monkeypatch.setattr(neatlogs, "span", exploding_span)
    except ImportError:
        pass

    r1 = run_act_one()
    _assert_canonical_act_one(r1)

    r2 = run_act_two()
    _assert_canonical_act_two(r2)


# ===========================================================================
# 3. Dodo Payments degradation
# ===========================================================================

def test_dodo_unconfigured():
    """DODO_API_KEY unset -> returns stub collection link, Act I succeeds with canonical numbers."""
    os.environ.pop("DODO_API_KEY", None)

    col = dodo_client.create_collection("CUST-4471", 263000.00)
    assert col["status"] == "stub"
    assert "pay_test_cust-4471_263000" in col["payment_link"]

    r1 = run_act_one()
    _assert_canonical_act_one(r1)
    s5 = next(s for s in r1["strata"] if s["classification"] == "LIVE_COLLECTIBLE_RECEIVABLE")
    assert s5["payment_link"] is not None


def test_dodo_unreachable_network_error(monkeypatch):
    """Dodo API configured but network call fails -> falls back to stub payment link."""
    os.environ["DODO_API_KEY"] = "dodo_test_key_123"

    import urllib.request
    def mock_urlopen(*args, **kwargs):
        raise urllib.error.URLError("Network unreachable")

    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)

    col = dodo_client.create_collection("CUST-4471", 263000.00)
    assert col["status"] == "stub"
    assert col["stub"] is True

    r1 = run_act_one()
    _assert_canonical_act_one(r1)


def test_dodo_client_raises(monkeypatch):
    """dodo_client.create_collection raises an exception -> act_one catches, logs, continues."""
    def exploding_create(*args, **kwargs):
        raise RuntimeError("Dodo Payments service completely down")

    monkeypatch.setattr(dodo_client, "create_collection", exploding_create)

    r1 = run_act_one()
    _assert_canonical_act_one(r1)
    s5 = next(s for s in r1["strata"] if s["classification"] == "LIVE_COLLECTIBLE_RECEIVABLE")
    assert s5["factor_usd"] == "263000.000"


# ===========================================================================
# 4. Tensormux gateway degradation
# ===========================================================================

def test_tensormux_unconfigured():
    """Tensormux credentials unset -> calls fallback to scripted stubs, cost meter tracks."""
    os.environ.pop("TENSORMUX_API_KEY", None)
    os.environ.pop("TENSORMUX_BASE_URL", None)

    assert not model._tensormux_configured()
    res_fast = model.call_fast("classify this")
    assert res_fast.content == model.SCRIPTED_FALLBACK_FAST

    res_strong = model.call_strong("reason about this")
    assert res_strong.content == model.SCRIPTED_FALLBACK_STRONG

    cost = model.get_cost_summary()
    assert cost["fast_calls"] >= 1
    assert cost["strong_calls"] >= 1

    r1 = run_act_one()
    _assert_canonical_act_one(r1)

    r2 = run_act_two()
    _assert_canonical_act_two(r2)


def test_tensormux_unreachable_network_error(monkeypatch):
    """Tensormux gateway endpoint unreachable -> catches network error, returns stub response."""
    os.environ["TENSORMUX_API_KEY"] = "tm_key_test"
    os.environ["TENSORMUX_BASE_URL"] = "https://api.tensormux.com"

    def mock_post(*args, **kwargs):
        raise requests.ConnectionError("Tensormux gateway connection timed out")

    monkeypatch.setattr(requests, "post", mock_post)

    res_fast = model.call_fast("test message")
    assert res_fast.content == model.SCRIPTED_FALLBACK_FAST

    res_strong = model.call_strong("test message")
    assert res_strong.content == model.SCRIPTED_FALLBACK_STRONG

    r1 = run_act_one()
    _assert_canonical_act_one(r1)

    r2 = run_act_two()
    _assert_canonical_act_two(r2)


# ===========================================================================
# 5. Voice briefing degradation
# ===========================================================================

def test_voice_unconfigured():
    """AI_GRANTS_VOICE_API_KEY unset -> returns briefing text with audio_url=None."""
    os.environ.pop("AI_GRANTS_VOICE_API_KEY", None)

    packet = {
        "entity_id": "ENT-IN-02",
        "period": "2026-03",
        "opening_deviation_usd": "44000.00",
        "explained_usd": "39000.00",
        "residual_usd": "5000.00",
        "evidence_gap": ["March billing-run config"],
    }
    briefing = voice_client.generate_escalation_briefing(packet)
    assert briefing["audio_url"] is None
    assert briefing["status"] == "unconfigured"
    assert "44,000" in briefing["text"]

    r1 = run_act_one()
    _assert_canonical_act_one(r1)

    r2 = run_act_two()
    _assert_canonical_act_two(r2)


def test_voice_unreachable_network_error(monkeypatch):
    """Voice synthesis API fails -> logs warning, returns fallback with audio_url=None."""
    os.environ["AI_GRANTS_VOICE_API_KEY"] = "voice_key_123"

    import urllib.request
    def mock_urlopen(*args, **kwargs):
        raise urllib.error.URLError("DNS resolution failed")

    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)

    packet = {"residual_usd": 5000.0, "evidence_gap": ["config export"]}
    briefing = voice_client.generate_escalation_briefing(packet)
    assert briefing["audio_url"] is None
    assert briefing["status"] == "fallback"

    r1 = run_act_one()
    _assert_canonical_act_one(r1)

    r2 = run_act_two()
    _assert_canonical_act_two(r2)


def test_voice_client_raises(monkeypatch):
    """Voice client raises -> tools.escalate swallows exception and returns packet."""
    def exploding_voice(*args, **kwargs):
        raise RuntimeError("Voice synthesis worker crashed")

    monkeypatch.setattr(voice_client, "generate_escalation_briefing", exploding_voice)

    r1 = run_act_one()
    _assert_canonical_act_one(r1)

    r2 = run_act_two()
    _assert_canonical_act_two(r2)


# ===========================================================================
# 6. Full network blackout — all integrations disabled simultaneously
# ===========================================================================

def test_all_integrations_disabled_simultaneously(monkeypatch):
    """Acceptance test: simulate total network blackout.

    Confirm that with all 5 integrations unreachable or unconfigured, both acts
    still complete with exact canonical numbers.
    """
    for key in [
        "AO_PROCESS_ID", "AO_WALLET_PATH", "AO_URL",
        "NEATLOGS_API_KEY", "NEATLOGS_TRACE_URL",
        "DODO_API_KEY", "DODO_BASE_URL",
        "TENSORMUX_API_KEY", "TENSORMUX_BASE_URL",
        "AI_GRANTS_VOICE_API_KEY", "AI_GRANTS_VOICE_ENDPOINT",
    ]:
        os.environ.pop(key, None)

    # Block socket connections to guarantee zero network
    orig_connect = socket.socket.connect
    def blocked_connect(*args, **kwargs):
        raise OSError("Network blackout simulation: all socket connections blocked")

    monkeypatch.setattr(socket.socket, "connect", blocked_connect)

    r1 = run_act_one(on_event=ao_client.handle_event)
    _assert_canonical_act_one(r1)

    r2 = run_act_two(on_event=ao_client.handle_event)
    _assert_canonical_act_two(r2)


# ===========================================================================
# 7. Replay fixture tests (demo insurance policy)
# ===========================================================================

def test_replay_act_one_produces_canonical_numbers():
    """Act I replay fixture completes with canonical numbers and zero live data hit."""
    result = run_act_one(replay=True, respect_timing=False)
    _assert_canonical_act_one(result)


def test_replay_act_two_produces_canonical_numbers():
    """Act II replay fixture completes with canonical numbers and zero live data hit."""
    result = run_act_two(replay=True, respect_timing=False)
    _assert_canonical_act_two(result)


def test_replay_with_network_disabled(monkeypatch):
    """Replay mode functions with the network fully disabled (README demo insurance policy)."""
    orig_connect = socket.socket.connect
    def blocked_connect(*args, **kwargs):
        raise OSError("Network disabled during replay")

    monkeypatch.setattr(socket.socket, "connect", blocked_connect)

    r1 = run_act_one(replay=True, respect_timing=False)
    _assert_canonical_act_one(r1)

    r2 = run_act_two(replay=True, respect_timing=False)
    _assert_canonical_act_two(r2)
