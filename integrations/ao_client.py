"""Agent Orchestrator (AO) ledger client (README.md §6.1, PHASE 4).

Dispatcher with a non-blocking send queue and a 2-second timeout.
Exposes:
  - record_step(payload: dict) -> None
  - record_decision(payload: dict) -> None
  - get_ledger_process_id() -> str | None
  - handle_event(event: dict) -> None

If AO_PROCESS_ID / AO_WALLET_PATH env vars are not set, or the local aos
process isn't reachable, logs and no-ops gracefully — never raises, never
blocks the caller (mirroring agent/model.py).
"""

import hashlib
import json
import logging
import os
import queue
import threading
import time
from typing import Any, Callable, Optional

try:
    import requests
except ImportError:
    requests = None  # type: ignore

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 2.0
_QUEUE_MAXSIZE = 1000

_send_queue: queue.Queue = queue.Queue(maxsize=_QUEUE_MAXSIZE)
_worker_thread: Optional[threading.Thread] = None
_worker_lock = threading.Lock()
_mock_sender: Optional[Callable[[str, dict, float], Any]] = None


def get_ledger_process_id() -> Optional[str]:
    """Returns the configured AO ledger process ID, or None if not set."""
    val = os.environ.get("AO_PROCESS_ID", "").strip()
    return val if val else None


def get_wallet_path() -> Optional[str]:
    """Returns the configured AO wallet path, or None if not set."""
    val = os.environ.get("AO_WALLET_PATH", "").strip()
    return val if val else None


def is_configured() -> bool:
    """Returns True if AO_PROCESS_ID and AO_WALLET_PATH are both configured."""
    return bool(get_ledger_process_id() and get_wallet_path())


def set_sender(sender_fn: Optional[Callable[[str, dict, float], Any]]) -> None:
    """Injects a custom/mock sender for testing or simulation."""
    global _mock_sender
    _mock_sender = sender_fn


def reset_client() -> None:
    """Flushes/drains the queue and resets test hooks."""
    global _mock_sender
    _mock_sender = None
    while not _send_queue.empty():
        try:
            _send_queue.get_nowait()
            _send_queue.task_done()
        except (queue.Empty, ValueError):
            break


def _ensure_worker_started() -> None:
    global _worker_thread
    if _worker_thread is not None and _worker_thread.is_alive():
        return
    with _worker_lock:
        if _worker_thread is None or not _worker_thread.is_alive():
            _worker_thread = threading.Thread(
                target=_worker_loop, daemon=True, name="ao_dispatcher_worker"
            )
            _worker_thread.start()


def _worker_loop() -> None:
    while True:
        try:
            item = _send_queue.get()
            if item is None:
                _send_queue.task_done()
                break
            action, payload = item
            try:
                _dispatch_message(action, payload, timeout=DEFAULT_TIMEOUT)
            except Exception as exc:
                logger.warning("AO background worker failed dispatching %s: %s", action, exc)
            finally:
                _send_queue.task_done()
        except Exception as exc:
            logger.warning("Unexpected error in AO worker loop: %s", exc)


def _dispatch_message(action: str, payload: dict, timeout: float = DEFAULT_TIMEOUT) -> Optional[dict]:
    """Dispatches a message to the AO process. Handles network failures gracefully."""
    if _mock_sender is not None:
        try:
            return _mock_sender(action, payload, timeout)
        except Exception as exc:
            logger.warning("AO mock sender failed (%s): %s", action, exc)
            return None

    if not is_configured():
        logger.debug("AO client not configured, skipping dispatch of %s", action)
        return None

    target = get_ledger_process_id()
    url = os.environ.get("AO_URL") or os.environ.get("AO_MU_URL") or "http://localhost:6363"

    message_body = {
        "Target": target,
        "Tags": [{"name": "Action", "value": action}],
        "Data": json.dumps(payload),
    }

    try:
        if requests is not None:
            resp = requests.post(url, json=message_body, timeout=timeout)
            if resp.status_code == 200:
                logger.debug("AO message (%s) dispatched successfully", action)
                try:
                    return resp.json()
                except Exception:
                    return {"ok": True, "text": resp.text}
            else:
                logger.warning(
                    "AO endpoint returned status %s for Action %s: %s",
                    resp.status_code,
                    action,
                    resp.text[:200] if resp.text else "",
                )
                return None
        else:
            import urllib.request
            req = urllib.request.Request(
                url,
                data=json.dumps(message_body).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=timeout) as response:
                body = response.read().decode("utf-8")
                try:
                    return json.loads(body)
                except Exception:
                    return {"ok": True, "text": body}
    except Exception as exc:
        logger.warning("AO process unreachable at %s for Action %s: %s", url, action, exc)
        return None


def _enqueue(action: str, payload: dict) -> None:
    """Non-blocking enqueue for outgoing AO messages."""
    if not is_configured() and _mock_sender is None:
        logger.info(
            "AO client not configured (AO_PROCESS_ID or AO_WALLET_PATH missing); no-op for %s",
            action,
        )
        return

    _ensure_worker_started()
    try:
        _send_queue.put_nowait((action, payload))
    except queue.Full:
        logger.warning("AO send queue full; dropping message for Action=%s", action)
    except Exception as exc:
        logger.warning("Failed to enqueue AO message (%s): %s", action, exc)


def record_step(payload: dict) -> None:
    """Records an accepted factor or rejected hypothesis to the AO ledger process.

    Expected payload keys (compatible with ao/reconfx_ledger.lua RecordStep handler):
      - act: "EXCAVATION" | "INVESTIGATION"
      - factor_id (or cause_id): str
      - classification: str
      - transaction_ids: list[str]
      - evidence_refs: list[str]
      - factor_usd: float | int | str
      - new_residual: float | int | str
      - accepted: bool
      - rejection_reason: str | None

    Non-blocking, never raises.
    """
    try:
        factor_id = payload.get("factor_id") or payload.get("cause_id", "")
        factor_usd = payload.get("factor_usd", 0.0)
        new_residual = payload.get("new_residual", 0.0)

        try:
            factor_usd_val = float(factor_usd)
        except (ValueError, TypeError):
            factor_usd_val = 0.0

        try:
            new_residual_val = float(new_residual)
        except (ValueError, TypeError):
            new_residual_val = 0.0

        norm_payload = {
            "act": str(payload.get("act", "")),
            "factor_id": str(factor_id),
            "classification": str(payload.get("classification", "")),
            "transaction_ids": list(payload.get("transaction_ids", [])),
            "evidence_refs": list(payload.get("evidence_refs", [])),
            "factor_usd": factor_usd_val,
            "new_residual": new_residual_val,
            "accepted": bool(payload.get("accepted", False)),
            "rejection_reason": payload.get("rejection_reason"),
        }
        _enqueue("RecordStep", norm_payload)
    except Exception as exc:
        logger.warning("Error in record_step: %s", exc)


def record_decision(payload: dict) -> None:
    """Records a controller decision (APPROVE_TRUEUP | APPROVE_COLLECTION | REJECT)
    to the AO ledger process.

    Expected payload keys (compatible with ao/reconfx_ledger.lua RecordDecision handler):
      - decision_type: "APPROVE_TRUEUP" | "APPROVE_COLLECTION" | "REJECT"
      - actor: str (default "controller")
      - payload_hash: str (computed from payload if not supplied)

    Non-blocking, never raises.
    """
    try:
        decision_type = payload.get("decision_type", "")
        actor = payload.get("actor", "controller")
        payload_hash = payload.get("payload_hash")
        if not payload_hash:
            payload_hash = hashlib.sha256(
                json.dumps(payload, sort_keys=True).encode("utf-8")
            ).hexdigest()

        norm_payload = {
            "decision_type": str(decision_type),
            "actor": str(actor),
            "payload_hash": str(payload_hash),
        }
        _enqueue("RecordDecision", norm_payload)
    except Exception as exc:
        logger.warning("Error in record_decision: %s", exc)


def query_ledger(timeout: float = DEFAULT_TIMEOUT) -> Optional[dict]:
    """Synchronously queries GetLedger from the AO process.
    Returns {"steps": [...], "decisions": [...], "residual": ...} or None.
    Never raises.
    """
    try:
        if _mock_sender is not None:
            return _mock_sender("GetLedger", {}, timeout)

        if not is_configured():
            logger.info("AO client not configured; query_ledger returns None")
            return None

        target = get_ledger_process_id()
        url = os.environ.get("AO_URL") or os.environ.get("AO_MU_URL") or "http://localhost:6363"

        message_body = {
            "Target": target,
            "Tags": [{"name": "Action", "value": "GetLedger"}],
            "Data": "{}",
        }
        if requests is not None:
            resp = requests.post(url, json=message_body, timeout=timeout)
            if resp.status_code == 200:
                return resp.json()
            return None
        else:
            import urllib.request
            req = urllib.request.Request(
                url,
                data=json.dumps(message_body).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        logger.warning("Failed to query GetLedger from AO: %s", exc)
        return None


def flush(timeout: float = DEFAULT_TIMEOUT) -> bool:
    """Waits up to `timeout` seconds for all pending queued messages to be processed.
    Returns True if queue drained, False on timeout.
    """
    start_time = time.time()
    while not _send_queue.empty() or _send_queue.unfinished_tasks > 0:
        if time.time() - start_time > timeout:
            return False
        time.sleep(0.01)
    return True


def handle_event(event: dict) -> None:
    """Event subscriber for ReActLoop event streams.
    Forwards test_hypothesis results and controller decisions to AO.
    Never raises.
    """
    try:
        if not isinstance(event, dict):
            return

        event_type = event.get("event_type")
        payload = event.get("payload")
        if not isinstance(payload, dict):
            return

        act = event.get("act", "")

        # Route 1: test_hypothesis tool call (contains full kwargs + result)
        if event_type == "TOOL_CALL" and payload.get("tool_name") == "test_hypothesis":
            kwargs = payload.get("kwargs", {})
            result = payload.get("result", {})
            record_step({
                "act": act,
                "factor_id": kwargs.get("cause_id", ""),
                "classification": kwargs.get("classification", ""),
                "transaction_ids": kwargs.get("transaction_ids", []),
                "evidence_refs": kwargs.get("evidence_refs", []),
                "factor_usd": result.get("factor_usd", 0.0),
                "new_residual": result.get("new_residual", 0.0),
                "accepted": result.get("accepted", False),
                "rejection_reason": result.get("rejection_reason"),
            })
        # Route 2: controller decision events
        elif event_type in ("DECISION", "CONTROLLER_DECISION", "RECORD_DECISION"):
            record_decision(payload)
        elif "decision_type" in payload and payload["decision_type"] in (
            "APPROVE_TRUEUP",
            "APPROVE_COLLECTION",
            "REJECT",
        ):
            record_decision(payload)
    except Exception as exc:
        logger.warning("Error in ao_client.handle_event: %s", exc)
