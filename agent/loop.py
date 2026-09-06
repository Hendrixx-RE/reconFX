"""ReAct loop for reconFX (PLAN.md §5.3 agent/loop.py).

Responsibilities:
  - hard step cap MAX_STEPS = 12, forced escalate() on breach
  - every step emits a state event (Appendix B schema) via an injected
    callback, so Phase 4's FastAPI/WebSocket layer can subscribe without
    loop.py knowing anything about FastAPI
  - structured tool-call parsing with a retry-once-then-escalate policy on
    malformed tool input, so the loop never crashes

No agent framework is used, per PLAN.md §5.1.
"""

from datetime import datetime, timezone
from typing import Callable, Optional

MAX_STEPS = 12


class LoopEscalated(Exception):
    """Raised when the loop halts and calls escalate(). Callers (act_one.py /
    act_two.py) catch this to stop the run cleanly."""

    def __init__(self, escalation_result: dict):
        self.escalation_result = escalation_result
        super().__init__(escalation_result.get("reason", "escalated"))


class ReActLoop:
    def __init__(
        self,
        act: str,
        escalate_fn: Callable[..., dict],
        on_event: Optional[Callable[[dict], None]] = None,
        max_steps: int = MAX_STEPS,
    ):
        """
        act:         "EXCAVATION" | "INVESTIGATION"
        escalate_fn: agent.tools.escalate, injected so this module has no
                     import-time dependency on tools.py (keeps it unit-testable
                     with a fake escalate_fn)
        on_event:    callback invoked with each event dict (Appendix B schema)
        """
        self.act = act
        self._escalate_fn = escalate_fn
        self._on_event = on_event or (lambda event: None)
        self._max_steps = max_steps
        self.step_count = 0
        self._malformed_retry_used = False

    def _emit(self, event_type: str, payload: dict) -> None:
        event = {
            "event_type": event_type,
            "act": self.act,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "step": self.step_count,
            "payload": payload,
        }
        self._on_event(event)

    def _check_step_cap(self) -> None:
        if self.step_count > self._max_steps:
            packet = {
                "reason": "MAX_STEPS_EXCEEDED",
                "step_count": self.step_count,
                "max_steps": self._max_steps,
            }
            result = self._escalate_fn(
                reason="MAX_STEPS_EXCEEDED",
                residual_usd=0.0,
                evidence_gap=["Loop exceeded step cap without reaching a terminal state"],
                packet=packet,
            )
            self._emit("ESCALATION", result)
            raise LoopEscalated(result)

    def call_tool(self, tool_name: str, tool_fn: Callable, kwargs: dict) -> dict:
        """Runs one tool call as one loop step. Emits a TOOL_CALL event on
        success. On malformed input (TypeError/ValueError from bad kwargs),
        retries once with the same kwargs, then escalates rather than
        crashing the run."""
        self.step_count += 1
        self._check_step_cap()

        try:
            result = tool_fn(**kwargs)
        except (TypeError, ValueError) as exc:
            if self._malformed_retry_used:
                packet = {
                    "reason": "MALFORMED_TOOL_CALL",
                    "tool_name": tool_name,
                    "kwargs": kwargs,
                    "error": str(exc),
                }
                esc_result = self._escalate_fn(
                    reason="MALFORMED_TOOL_CALL",
                    residual_usd=0.0,
                    evidence_gap=[f"Well-formed arguments for tool '{tool_name}'"],
                    packet=packet,
                )
                self._emit("ESCALATION", esc_result)
                raise LoopEscalated(esc_result) from exc

            self._malformed_retry_used = True
            self._emit(
                "TOOL_CALL",
                {"tool_name": tool_name, "kwargs": kwargs, "retry": True, "error": str(exc)},
            )
            return self.call_tool(tool_name, tool_fn, kwargs)

        self._emit("TOOL_CALL", {"tool_name": tool_name, "kwargs": kwargs, "result": result})
        return result

    def record_hypothesis_event(self, event_type: str, payload: dict) -> None:
        """For HYPOTHESIS / FACTOR_ACCEPTED / FACTOR_REJECTED / RECOVERY_FOUND /
        DISPOSITION events that aren't themselves a tool call (e.g. the
        LLM's stated hypothesis text, or a disposition assignment)."""
        self._emit(event_type, payload)

    def escalate(self, reason: str, residual_usd: float, evidence_gap: list[str], packet: dict) -> None:
        """Explicit escalation path (not step-cap driven), e.g. an
        unresolved residual at the end of hypothesis testing."""
        result = self._escalate_fn(
            reason=reason, residual_usd=residual_usd, evidence_gap=evidence_gap, packet=packet
        )
        self._emit("ESCALATION", result)
        raise LoopEscalated(result)
