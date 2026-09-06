"""AI Grants India voice integration (Phase 4, Priority 5 - Optional).

Generates a short (~20-second) spoken briefing summarizing:
- what was found (opening deviation)
- what was explained (explained variance)
- what remains (residual variance)
- what evidence would close it (evidence gap)

Per README Section 6.6 and Appendix C escalation packet schema.
Gated behind AI_GRANTS_VOICE_API_KEY. Falls back gracefully to a stub (audio_url: None)
when unconfigured or on any failure -- never raises, never blocks.
"""

import json
import logging
import os
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

ENV_VOICE_API_KEY = "AI_GRANTS_VOICE_API_KEY"
ENV_VOICE_ENDPOINT = "AI_GRANTS_VOICE_ENDPOINT"
DEFAULT_VOICE_ENDPOINT = "https://api.aigrants.in/v1/voice/synthesize"
DEFAULT_TIMEOUT_SECONDS = 3.0
TARGET_DURATION_SECONDS = 20


def _format_usd(val: Any) -> Optional[str]:
    """Format an amount as USD string (e.g. $44,000 or $44,000.50)."""
    if val is None:
        return None
    try:
        f = float(val)
        if f.is_integer():
            return f"${int(f):,}"
        return f"${f:,.2f}"
    except (ValueError, TypeError):
        return f"${val}"


def compose_briefing_text(escalation_packet: Dict[str, Any]) -> str:
    """Compose a spoken briefing (~20 seconds) from an escalation packet."""
    if not isinstance(escalation_packet, dict):
        return (
            "Controller escalation briefing: An unexplained balance requires review. "
            "Supporting documentation is needed to close the gap."
        )

    entity_id = escalation_packet.get("entity_id")
    period = escalation_packet.get("period")
    opening = escalation_packet.get("opening_deviation_usd")
    explained = escalation_packet.get("explained_usd")
    residual = escalation_packet.get("residual_usd")
    evidence_gap = escalation_packet.get("evidence_gap")

    parts: List[str] = []

    # Header
    header_items = []
    if entity_id:
        header_items.append(f"entity {entity_id}")
    if period:
        header_items.append(f"period {period}")

    if header_items:
        parts.append(f"Controller escalation briefing for {', '.join(header_items)}.")
    else:
        parts.append("Controller escalation briefing.")

    # Opening deviation (what was found)
    opening_str = _format_usd(opening)
    explained_str = _format_usd(explained)
    residual_str = _format_usd(residual)

    if opening_str:
        parts.append(f"An opening deviation of {opening_str} was identified.")
    elif explained_str and residual_str:
        try:
            total_dev = float(explained) + float(residual)
            parts.append(f"An opening deviation of {_format_usd(total_dev)} was identified.")
        except Exception:
            pass

    # What was explained and what remains
    if explained_str and residual_str:
        parts.append(
            f"Investigations explained {explained_str}, leaving an unexplained residual of {residual_str}."
        )
    elif residual_str:
        parts.append(f"An unexplained residual of {residual_str} remains.")
    elif explained_str:
        parts.append(f"Investigations explained {explained_str}.")

    # What evidence would close it
    if isinstance(evidence_gap, list) and evidence_gap:
        clean_items = [str(g).strip() for g in evidence_gap if str(g).strip()]
        if len(clean_items) == 1:
            parts.append(f"To close this gap, the required evidence is: {clean_items[0]}.")
        elif len(clean_items) > 1:
            gap_summary = "; ".join(clean_items)
            parts.append(f"To close this gap, the following evidence is required: {gap_summary}.")
        else:
            parts.append("Supporting documentation is required to resolve this residual.")
    elif isinstance(evidence_gap, str) and evidence_gap.strip():
        parts.append(f"To close this gap, the required evidence is: {evidence_gap.strip()}.")
    else:
        parts.append("Supporting documentation is required to resolve this residual.")

    return " ".join(parts)


def generate_escalation_briefing(escalation_packet: dict) -> dict:
    """Generate a spoken controller briefing from an escalation packet.

    Summarizes:
    - what was found (opening_deviation_usd)
    - what was explained (explained_usd)
    - what remains (residual_usd)
    - what evidence would close it (evidence_gap)

    Interface:
    - Calls text-to-speech API if AI_GRANTS_VOICE_API_KEY is configured.
    - Gracefully falls back to stub (audio_url: None) if unconfigured or on any failure.
    - Never raises, never blocks.
    """
    try:
        briefing_text = compose_briefing_text(escalation_packet)
    except Exception as exc:
        logger.warning("Failed to compose briefing text: %s", exc)
        briefing_text = (
            "Controller escalation briefing: An unexplained balance requires review. "
            "Supporting documentation is needed to close the gap."
        )

    word_count = len(briefing_text.split())
    est_duration = max(5, round(word_count / 2.5)) if word_count > 0 else TARGET_DURATION_SECONDS

    api_key = os.getenv(ENV_VOICE_API_KEY, "").strip()
    if not api_key:
        return {
            "text": briefing_text,
            "briefing_text": briefing_text,
            "audio_url": None,
            "duration_seconds": est_duration,
            "status": "unconfigured",
        }

    endpoint = os.getenv(ENV_VOICE_ENDPOINT, DEFAULT_VOICE_ENDPOINT).strip()

    try:
        payload = json.dumps({
            "text": briefing_text,
            "voice": "controller",
            "format": "mp3",
        }).encode("utf-8")

        req = urllib.request.Request(
            endpoint,
            data=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "User-Agent": "reconFX-VoiceClient/1.0",
            },
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=DEFAULT_TIMEOUT_SECONDS) as response:
            resp_body = response.read().decode("utf-8")
            data = json.loads(resp_body) if resp_body else {}
            audio_url = data.get("audio_url") or data.get("url")
            return {
                "text": briefing_text,
                "briefing_text": briefing_text,
                "audio_url": audio_url,
                "duration_seconds": est_duration,
                "status": "synthesized" if audio_url else "stub",
            }
    except Exception as exc:
        logger.warning("Voice synthesis API call failed (%s): %s", endpoint, exc)
        return {
            "text": briefing_text,
            "briefing_text": briefing_text,
            "audio_url": None,
            "duration_seconds": est_duration,
            "status": "fallback",
            "error": str(exc),
        }
