"""Tensormux gateway client (README.md §5.3, §6.5).

Two named routes: call_fast (bulk classification, high volume/low judgment)
and call_strong (policy interpretation, precedence, memo narrative reading).
Call counts per route are tracked module-level so the console cost meter
(Phase 4/5) can read them without threading state through the agent loop.

This is a stub until TENSORMUX_API_KEY / TENSORMUX_BASE_URL are wired in
Phase 4. It always uses the SCRIPTED_FALLBACK path below, which lets
act_one.py / act_two.py run deterministically end-to-end without any
network dependency — required by the Phase 3 acceptance test that Act II's
numbers are identical across repeated runs.
"""

import os
from dataclasses import dataclass, field

_COUNTS = {"fast": 0, "strong": 0}


@dataclass
class ModelResponse:
    content: str
    tool_calls: list[dict] = field(default_factory=list)
    route: str = "fast"


def get_call_counts() -> dict:
    return dict(_COUNTS)


def reset_call_counts() -> None:
    _COUNTS["fast"] = 0
    _COUNTS["strong"] = 0


def _tensormux_configured() -> bool:
    return bool(os.environ.get("TENSORMUX_API_KEY")) and bool(
        os.environ.get("TENSORMUX_BASE_URL")
    )


def call_fast(messages: list[dict], tools: list[dict] | None = None) -> ModelResponse:
    """Bulk classification route — fast, cheap model."""
    _COUNTS["fast"] += 1
    if _tensormux_configured():
        raise NotImplementedError("Real Tensormux call wiring lands in Phase 4")
    return ModelResponse(content="[fast-route stub: no live model configured]", route="fast")


def call_strong(messages: list[dict], tools: list[dict] | None = None) -> ModelResponse:
    """Policy reasoning, memo narrative, precedence route — strong model."""
    _COUNTS["strong"] += 1
    if _tensormux_configured():
        raise NotImplementedError("Real Tensormux call wiring lands in Phase 4")
    return ModelResponse(content="[strong-route stub: no live model configured]", route="strong")
