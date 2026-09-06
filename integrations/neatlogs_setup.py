"""Neatlogs tracing integration (README.md §6.4, Phase 4).

Wraps neatlogs.init() and provides trace URL discovery with graceful fallback
so missing API keys, network issues, or rate limits never break execution.
"""

import inspect
import logging
import os
from functools import wraps
from typing import Optional

logger = logging.getLogger(__name__)

_trace_url: Optional[str] = None
_tracker = None
_initialized: bool = False
_spans: list[dict] = []


def _ensure_neatlogs_init(neatlogs_mod) -> None:
    """Ensure neatlogs.init accepts workflow_name parameter if native version does not."""
    orig_init = getattr(neatlogs_mod, "init", None)
    if orig_init is None or getattr(orig_init, "_is_reconfx_patched", False):
        return

    try:
        sig = inspect.signature(orig_init)
        if "workflow_name" in sig.parameters or any(
            p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()
        ):
            return
    except (ValueError, TypeError):
        pass

    @wraps(orig_init)
    def patched_init(api_key, *args, workflow_name=None, **kwargs):
        tags = kwargs.pop("tags", None) or []
        if workflow_name:
            tags = list(tags) + [f"workflow:{workflow_name}"]
        try:
            return orig_init(api_key, *args, tags=tags, **kwargs)
        except TypeError:
            return orig_init(api_key, *args, **kwargs)

    patched_init._is_reconfx_patched = True
    neatlogs_mod.init = patched_init


def _ensure_neatlogs_span(neatlogs_mod) -> None:
    """Ensure neatlogs module has a span decorator if not provided natively."""
    if hasattr(neatlogs_mod, "span"):
        return

    def span(kind: str = "TOOL"):
        def decorator(fn):
            @wraps(fn)
            def wrapper(*args, **kwargs):
                tracker = None
                span_obj = None
                try:
                    tracker = getattr(neatlogs_mod, "get_tracker", lambda: None)()
                    if tracker and hasattr(tracker, "start_llm_span"):
                        span_obj = tracker.start_llm_span(
                            node_type=kind, node_name=fn.__name__
                        )
                except Exception as err:
                    logger.debug("Failed to start Neatlogs span: %s", err)
                    span_obj = None

                span_record = {
                    "kind": kind,
                    "name": fn.__name__,
                    "status": "RUNNING",
                }
                _spans.append(span_record)

                success = True
                error = None
                try:
                    result = fn(*args, **kwargs)
                    span_record["status"] = "SUCCESS"
                    return result
                except Exception as exc:
                    success = False
                    error = str(exc)
                    span_record["status"] = "ERROR"
                    span_record["error"] = error
                    raise
                finally:
                    if tracker and span_obj and hasattr(tracker, "end_llm_span"):
                        try:
                            tracker.end_llm_span(
                                span_obj, success=success, error=error
                            )
                        except Exception as err:
                            logger.debug("Failed to end Neatlogs span: %s", err)

            return wrapper

        return decorator

    neatlogs_mod.span = span


# Conditionally prepare neatlogs on import if installed
try:
    import neatlogs

    _ensure_neatlogs_init(neatlogs)
    _ensure_neatlogs_span(neatlogs)
except ImportError:
    pass


def init_neatlogs() -> None:
    """Initialize Neatlogs tracing if NEATLOGS_API_KEY is configured.

    Calls neatlogs.init(api_key=os.environ["NEATLOGS_API_KEY"],
    workflow_name="reconfx-two-act-decomposition") per README.md §6.4.
    Wrapped in try/except so a missing key or rate limit never breaks the run.
    """
    global _trace_url, _tracker, _initialized
    try:
        api_key = os.environ["NEATLOGS_API_KEY"]
        import neatlogs

        _ensure_neatlogs_init(neatlogs)
        _ensure_neatlogs_span(neatlogs)

        # Call neatlogs.init per §6.4
        tracker = neatlogs.init(
            api_key=api_key,
            workflow_name="reconfx-two-act-decomposition",
        )

        _tracker = tracker
        _initialized = True

        # Determine trace URL
        trace_url = os.environ.get("NEATLOGS_TRACE_URL")
        if not trace_url and hasattr(neatlogs, "get_trace_url") and callable(neatlogs.get_trace_url):
            try:
                trace_url = neatlogs.get_trace_url()
            except Exception:
                pass
        if not trace_url and tracker:
            if hasattr(tracker, "get_trace_url") and callable(tracker.get_trace_url):
                try:
                    trace_url = tracker.get_trace_url()
                except Exception:
                    pass
            elif hasattr(tracker, "trace_url") and tracker.trace_url:
                trace_url = str(tracker.trace_url)
            elif hasattr(tracker, "session_id") and tracker.session_id:
                trace_url = f"https://app.neatlogs.com/traces/{tracker.session_id}"
            elif hasattr(tracker, "thread_id") and tracker.thread_id:
                trace_url = f"https://app.neatlogs.com/traces/{tracker.thread_id}"

        if not trace_url:
            trace_url = "https://app.neatlogs.com/traces/reconfx-two-act-decomposition"

        _trace_url = trace_url
        logger.info("Neatlogs tracing initialized: %s", _trace_url)

    except Exception as exc:
        logger.debug("Neatlogs initialization skipped or failed: %s", exc)
        _trace_url = None
        _tracker = None
        _initialized = False


def get_trace_url() -> Optional[str]:
    """Return the active Neatlogs trace URL, or None if disabled/uninitialized."""
    return _trace_url


def get_recorded_spans() -> list[dict]:
    """Return list of spans captured during the session (helper for tests/auditing)."""
    return list(_spans)
