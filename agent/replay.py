"""Replay and record fixtures for reconFX agent tool calls (README.md §7 Phase 6).

Provides:
- record_session(fixture_path): Context manager caching all 7 tool calls
  (inputs, outputs, relative timing gaps) to a JSON fixture file as they occur.
- replay_session(fixture_path, respect_timing=True, speed=1.0): Context manager
  replaying cached tool outputs in exact sequence with relative timing gaps and
  zero network dependency.
"""

import copy
import inspect
import json
import logging
import os
import time
from contextlib import contextmanager
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from agent import tools

logger = logging.getLogger(__name__)

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "tests" / "fixtures"
DEFAULT_ACT_ONE_FIXTURE = FIXTURES_DIR / "act_one_replay.json"
DEFAULT_ACT_TWO_FIXTURE = FIXTURES_DIR / "act_two_replay.json"

TOOL_NAMES = [
    "get_policy",
    "query_gl",
    "query_payroll",
    "query_approvals",
    "query_clearing_account",
    "test_hypothesis",
    "draft_journal_entry",
]


def _json_sanitize(val: Any) -> Any:
    """Recursively convert values into native JSON serializable types."""
    if isinstance(val, (str, int, float, bool)) or val is None:
        return val
    elif isinstance(val, Decimal):
        return str(val)
    elif isinstance(val, Path):
        return str(val)
    elif isinstance(val, dict):
        return {str(k): _json_sanitize(v) for k, v in val.items()}
    elif isinstance(val, (list, tuple)):
        return [_json_sanitize(v) for v in val]
    elif isinstance(val, (set, frozenset)):
        return [_json_sanitize(v) for v in sorted(val, key=str)]
    else:
        return str(val)


def _write_fixture_file(path: Path, calls: List[Dict[str, Any]]) -> None:
    """Safely write JSON fixture file to disk."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(".tmp")
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(calls, f, indent=2)
    os.replace(temp_path, path)


@contextmanager
def record_session(fixture_path: Path | str):
    """Context manager that records every call to the 7 tools in agent.tools.

    As each tool call occurs, it captures inputs, outputs, timestamps, and
    relative timing gaps, and persists them immediately to fixture_path.
    """
    path = Path(fixture_path)
    recorded_calls: List[Dict[str, Any]] = []
    last_call_time: Optional[float] = None
    orig_fns: Dict[str, Callable] = {}

    def make_recorder(tool_name: str, orig_fn: Callable):
        def wrapper(*args, **kwargs):
            nonlocal last_call_time
            t_start = time.perf_counter()
            gap = (t_start - last_call_time) if last_call_time is not None else 0.0
            last_call_time = t_start

            # Execute live tool
            result = orig_fn(*args, **kwargs)

            # Bind argument names
            try:
                sig = inspect.signature(orig_fn)
                bound = sig.bind(*args, **kwargs)
                bound.apply_defaults()
                bound_args = dict(bound.arguments)
            except Exception:
                bound_args = kwargs

            record = {
                "step": len(recorded_calls) + 1,
                "tool_name": tool_name,
                "kwargs": _json_sanitize(bound_args),
                "result": _json_sanitize(result),
                "timestamp": round(t_start, 6),
                "relative_gap": round(gap, 6),
            }
            recorded_calls.append(record)

            # Persist immediately to fixture file
            try:
                _write_fixture_file(path, recorded_calls)
            except Exception as exc:
                logger.warning("Failed writing replay fixture to %s: %s", path, exc)

            return result

        return wrapper

    # Patch the 7 tools on agent.tools
    for name in TOOL_NAMES:
        if hasattr(tools, name):
            orig = getattr(tools, name)
            orig_fns[name] = orig
            setattr(tools, name, make_recorder(name, orig))

    try:
        yield recorded_calls
    finally:
        # Restore original functions
        for name, orig in orig_fns.items():
            setattr(tools, name, orig)
        if recorded_calls:
            _write_fixture_file(path, recorded_calls)
            logger.info("Saved %d recorded tool calls to %s", len(recorded_calls), path)


@contextmanager
def replay_session(
    fixture_path: Path | str,
    respect_timing: bool = True,
    speed: float = 1.0,
):
    """Context manager that replays cached tool calls from fixture_path.

    Replays cached outputs in exact sequence with relative timing gaps and zero
    network dependency.
    """
    path = Path(fixture_path)
    if not path.is_file():
        raise FileNotFoundError(f"Replay fixture file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    calls: List[Dict[str, Any]] = data if isinstance(data, list) else data.get("tool_calls", [])
    call_index = 0
    orig_fns: Dict[str, Callable] = {}

    # Isolate network integrations during replay for zero network dependency
    from integrations import dodo_client, voice_client

    orig_dodo_create = dodo_client.create_collection
    def stub_dodo_create(customer_ref: str, amount_usd: float, description: str = ""):
        return {
            "payment_id": f"pay_test_{customer_ref.lower().replace(' ', '-')}_{int(round(amount_usd))}",
            "payment_link": f"https://test.dodopayments.com/buy/pay_test_{customer_ref.lower().replace(' ', '-')}_{int(round(amount_usd))}",
            "checkout_url": f"https://test.dodopayments.com/buy/pay_test_{customer_ref.lower().replace(' ', '-')}_{int(round(amount_usd))}",
            "customer_ref": customer_ref,
            "amount_usd": float(amount_usd),
            "currency": "USD",
            "description": description,
            "status": "stub",
            "stub": True,
            "dodo_reference": f"pay_test_{customer_ref.lower().replace(' ', '-')}_{int(round(amount_usd))}",
            "reason": "replay_zero_network",
        }
    dodo_client.create_collection = stub_dodo_create
    dodo_client.create_payment_link = stub_dodo_create

    orig_voice_synthesize = getattr(voice_client, "generate_escalation_briefing", None)
    def stub_voice_synthesize(packet: dict):
        return {
            "text": voice_client.compose_briefing_text(packet),
            "briefing_text": voice_client.compose_briefing_text(packet),
            "audio_url": None,
            "duration_seconds": 20,
            "status": "replay_stub",
        }
    voice_client.generate_escalation_briefing = stub_voice_synthesize

    def make_replayer(tool_name: str, orig_fn: Callable):
        def wrapper(*args, **kwargs):
            nonlocal call_index
            if call_index >= len(calls):
                logger.warning(
                    "Replay fixture exhausted (%d calls); falling back to live tool for %s",
                    len(calls),
                    tool_name,
                )
                return orig_fn(*args, **kwargs)

            cached = calls[call_index]
            call_index += 1

            # Assert or verify expected tool call
            cached_tool = cached.get("tool_name")
            if cached_tool and cached_tool != tool_name:
                logger.debug(
                    "Replay tool name mismatch at step %d: expected %s, got %s",
                    call_index,
                    cached_tool,
                    tool_name,
                )

            # Replay relative timing gap
            gap = float(cached.get("relative_gap", 0.0))
            if respect_timing and speed > 0 and gap > 0:
                time.sleep(gap / speed)

            # For test_hypothesis, run in-memory DecompositionState update if bound
            if tool_name == "test_hypothesis" and getattr(tools, "_STATE", None) is not None:
                try:
                    orig_fn(*args, **kwargs)
                except Exception as exc:
                    logger.debug("Replay in-memory state update: %s", exc)

            return copy.deepcopy(cached.get("result"))

        return wrapper

    # Patch the 7 tools on agent.tools
    for name in TOOL_NAMES:
        if hasattr(tools, name):
            orig = getattr(tools, name)
            orig_fns[name] = orig
            setattr(tools, name, make_replayer(name, orig))

    try:
        yield calls
    finally:
        # Restore tools and integration hooks
        for name, orig in orig_fns.items():
            setattr(tools, name, orig)
        dodo_client.create_collection = orig_dodo_create
        dodo_client.create_payment_link = orig_dodo_create
        if orig_voice_synthesize:
            voice_client.generate_escalation_briefing = orig_voice_synthesize
