"""Tensormux gateway client (README.md §5.3, §6.5, Phase 4).

Two named routes: call_fast (bulk classification, high volume/low judgment)
and call_strong (policy interpretation, precedence, memo narrative reading).
Call counts and cost per route are tracked module-level so the console cost
meter (Phase 4/5) can read them via get_call_counts() / get_cost_summary()
without threading state through the agent loop.

When TENSORMUX_API_KEY and TENSORMUX_BASE_URL are configured, calls are
dispatched via HTTP to the Tensormux gateway. If the gateway call fails for
any reason (network timeout, authentication error, 5xx server response, or
malformed payload), the error is logged and the client falls back to the
deterministic scripted stub response. This guarantees that Act II's financial
decomposition remains reproducible and resilient across runs, even under network
faults.
"""

import logging
import os
from dataclasses import dataclass, field
from typing import Any, Optional

import requests

logger = logging.getLogger(__name__)

# Module-level counters for Tensormux cost meter (README.md §6.5, Phase 4)
_COUNTS = {"fast": 0, "strong": 0}
_USAGE = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

# Fallback response stubs ensuring deterministic degradation
SCRIPTED_FALLBACK_FAST = "[fast-route stub: no live model configured]"
SCRIPTED_FALLBACK_STRONG = "[strong-route stub: no live model configured]"

# Routing defaults per README.md §6.5
# call_fast -> fast, cheap model (bulk classification)
# call_strong -> strong model (policy reasoning, precedence, memos)
DEFAULT_FAST_MODEL = "gpt-4o-mini"
DEFAULT_STRONG_MODEL = "gpt-4o"

# Estimated nominal USD cost per call for console cost footer (§6.5: "Fast: 6 calls · Strong: 4 calls · $0.--")
DEFAULT_COST_PER_FAST = 0.001
DEFAULT_COST_PER_STRONG = 0.008


@dataclass
class ModelResponse:
    content: str
    tool_calls: list[dict] = field(default_factory=list)
    route: str = "fast"


def get_call_counts() -> dict:
    """Return dictionary of call counts per route."""
    return dict(_COUNTS)


def reset_call_counts() -> None:
    """Reset call counts and token usage meters."""
    _COUNTS["fast"] = 0
    _COUNTS["strong"] = 0
    _USAGE["prompt_tokens"] = 0
    _USAGE["completion_tokens"] = 0
    _USAGE["total_tokens"] = 0


def get_cost_summary() -> dict:
    """Return per-route call counts, estimated USD cost, and formatted footer.

    Matches README.md §6.5 console footer format:
    e.g. 'Fast: 6 calls · Strong: 4 calls · $0.04'
    """
    counts = get_call_counts()
    fast_calls = counts.get("fast", 0)
    strong_calls = counts.get("strong", 0)
    total_calls = fast_calls + strong_calls

    try:
        fast_rate = float(os.environ.get("TENSORMUX_COST_PER_FAST", DEFAULT_COST_PER_FAST))
    except (ValueError, TypeError):
        fast_rate = DEFAULT_COST_PER_FAST

    try:
        strong_rate = float(os.environ.get("TENSORMUX_COST_PER_STRONG", DEFAULT_COST_PER_STRONG))
    except (ValueError, TypeError):
        strong_rate = DEFAULT_COST_PER_STRONG

    estimated_cost = (fast_calls * fast_rate) + (strong_calls * strong_rate)
    estimated_cost_usd = round(estimated_cost, 4)

    formatted = (
        f"Fast: {fast_calls} calls · Strong: {strong_calls} calls · ${estimated_cost:.2f}"
    )

    return {
        "fast_calls": fast_calls,
        "strong_calls": strong_calls,
        "fast": fast_calls,
        "strong": strong_calls,
        "total_calls": total_calls,
        "estimated_cost_usd": estimated_cost_usd,
        "cost_usd": estimated_cost_usd,
        "formatted": formatted,
    }


def _tensormux_configured() -> bool:
    """Return True if Tensormux credentials and endpoint are present in environment."""
    return bool(os.environ.get("TENSORMUX_API_KEY")) and bool(
        os.environ.get("TENSORMUX_BASE_URL")
    )


def _get_chat_endpoint(base_url: str) -> str:
    """Resolve base URL to the chat completions endpoint."""
    url = base_url.strip().rstrip("/")
    if url.endswith("/chat/completions"):
        return url
    if not url.endswith("/v1") and "/v1/" not in url:
        return f"{url}/v1/chat/completions"
    return f"{url}/chat/completions"


def _call_tensormux(
    route: str,
    model: str,
    messages: list[dict] | str,
    tools: list[dict] | None = None,
    fallback_content: str = SCRIPTED_FALLBACK_FAST,
) -> ModelResponse:
    """Execute HTTP request to Tensormux gateway with graceful error fallback."""
    api_key = os.environ.get("TENSORMUX_API_KEY", "")
    base_url = os.environ.get("TENSORMUX_BASE_URL", "")

    endpoint = _get_chat_endpoint(base_url)
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "x-api-key": api_key,
    }

    if isinstance(messages, str):
        msg_payload = [{"role": "user", "content": messages}]
    else:
        msg_payload = messages

    payload: dict[str, Any] = {
        "model": model,
        "messages": msg_payload,
    }
    if tools:
        payload["tools"] = tools

    try:
        timeout = float(os.environ.get("TENSORMUX_TIMEOUT", "10.0"))
    except (ValueError, TypeError):
        timeout = 10.0

    try:
        response = requests.post(
            endpoint,
            headers=headers,
            json=payload,
            timeout=timeout,
        )
        if response.status_code != 200:
            logger.warning(
                "Tensormux %s-route HTTP error %d: %s; falling back to stub response",
                route,
                response.status_code,
                response.text[:200],
            )
            return ModelResponse(content=fallback_content, route=route)

        data = response.json()
        choices = data.get("choices") or []
        if choices:
            msg = choices[0].get("message") or {}
            content = msg.get("content") or ""
            tool_calls = msg.get("tool_calls") or []
        else:
            content = ""
            tool_calls = []

        usage = data.get("usage")
        if usage and isinstance(usage, dict):
            _USAGE["prompt_tokens"] += usage.get("prompt_tokens", 0)
            _USAGE["completion_tokens"] += usage.get("completion_tokens", 0)
            _USAGE["total_tokens"] += usage.get("total_tokens", 0)

        logger.info("Tensormux %s-route call succeeded (model=%s)", route, model)
        return ModelResponse(
            content=content if (content or tool_calls) else fallback_content,
            tool_calls=tool_calls,
            route=route,
        )

    except Exception as exc:
        logger.warning(
            "Tensormux %s-route call failed (%s: %s); falling back to stub response",
            route,
            type(exc).__name__,
            exc,
        )
        return ModelResponse(content=fallback_content, route=route)


def call_fast(messages: list[dict] | str, tools: list[dict] | None = None) -> ModelResponse:
    """Bulk classification route — fast, cheap model."""
    _COUNTS["fast"] += 1
    if not _tensormux_configured():
        return ModelResponse(content=SCRIPTED_FALLBACK_FAST, route="fast")

    fast_model = (
        os.environ.get("TENSORMUX_MODEL_FAST")
        or os.environ.get("TENSORMUX_FAST_MODEL")
        or DEFAULT_FAST_MODEL
    )
    return _call_tensormux(
        route="fast",
        model=fast_model,
        messages=messages,
        tools=tools,
        fallback_content=SCRIPTED_FALLBACK_FAST,
    )


def call_strong(messages: list[dict] | str, tools: list[dict] | None = None) -> ModelResponse:
    """Policy reasoning, memo narrative, precedence route — strong model."""
    _COUNTS["strong"] += 1
    if not _tensormux_configured():
        return ModelResponse(content=SCRIPTED_FALLBACK_STRONG, route="strong")

    strong_model = (
        os.environ.get("TENSORMUX_MODEL_STRONG")
        or os.environ.get("TENSORMUX_STRONG_MODEL")
        or DEFAULT_STRONG_MODEL
    )
    return _call_tensormux(
        route="strong",
        model=strong_model,
        messages=messages,
        tools=tools,
        fallback_content=SCRIPTED_FALLBACK_STRONG,
    )
