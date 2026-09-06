"""Dodo Payments integration client for reconFX (README.md §6.3, §7 Phase 4).

Wraps Dodo Payments test-mode REST API for customer receivable collection.
Degrades gracefully: if DODO_API_KEY is not configured or the network / API call fails,
returns a stub hosted payment link and logs a warning — never raises, never blocks the caller.
"""

import json
import logging
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("integrations.dodo_client")

DEFAULT_TIMEOUT_SECONDS = 3.0


def _load_env_fallback() -> None:
    """Reads .env file into os.environ if present and not already set."""
    env_file = Path(__file__).resolve().parent.parent / ".env"
    if env_file.is_file():
        try:
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k, v = k.strip(), v.strip()
                        if k and k not in os.environ:
                            os.environ[k] = v
        except Exception as e:
            logger.debug("Could not read .env file: %s", e)


def _get_config() -> tuple[str, str, str]:
    """Returns (api_key, env, base_url)."""
    _load_env_fallback()
    api_key = os.environ.get("DODO_API_KEY", "").strip()
    env = os.environ.get("DODO_ENV", "test").strip().lower()

    if os.environ.get("DODO_BASE_URL"):
        base_url = os.environ["DODO_BASE_URL"].rstrip("/")
    elif env in ("live", "production"):
        base_url = "https://api.dodopayments.com"
    else:
        base_url = "https://test.dodopayments.com"

    return api_key, env, base_url


def _make_stub_collection(
    customer_ref: str,
    amount_usd: float,
    description: str,
    reason: str = "",
) -> Dict[str, Any]:
    """Generates a realistic test-mode stub payment link when API is unconfigured or unreachable."""
    clean_ref = customer_ref.strip().replace(" ", "-")
    clean_amount = int(round(amount_usd))
    payment_id = f"pay_test_{clean_ref.lower()}_{clean_amount}"
    hosted_link = f"https://test.dodopayments.com/buy/{payment_id}"

    logger.warning(
        "Dodo Payments fallback active (reason: %s). Returning stub payment link for %s ($%.2f): %s",
        reason or "unconfigured/offline",
        customer_ref,
        amount_usd,
        hosted_link,
    )

    return {
        "payment_id": payment_id,
        "payment_link": hosted_link,
        "checkout_url": hosted_link,
        "customer_ref": customer_ref,
        "amount_usd": float(amount_usd),
        "currency": "USD",
        "description": description,
        "status": "stub",
        "stub": True,
        "dodo_reference": payment_id,
        "reason": reason or "stub_fallback",
    }


def _http_post_json(url: str, payload: dict, api_key: str, timeout: float = DEFAULT_TIMEOUT_SECONDS) -> dict:
    """Performs an HTTP POST request sending and expecting JSON."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "reconFX-agent/1.0",
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")

    with urllib.request.urlopen(req, timeout=timeout) as response:
        body = response.read().decode("utf-8")
        return json.loads(body) if body else {}


def create_collection(
    customer_ref: str,
    amount_usd: float,
    description: str = "Customer receivable collection",
) -> Dict[str, Any]:
    """Creates a hosted payment collection link for a receivable in Dodo Payments test mode.

    Args:
        customer_ref: Customer reference identifier (e.g. "CUST-4471").
        amount_usd: Collection amount in USD (e.g. 263000.00).
        description: Description of the collection item.

    Returns:
        A dict containing payment_link, payment_id, customer_ref, amount_usd, etc.
        If DODO_API_KEY is missing or the API call fails, returns a stub payment link.
        Never raises exceptions and never blocks the caller.
    """
    try:
        api_key, env, base_url = _get_config()

        if not api_key:
            return _make_stub_collection(
                customer_ref=customer_ref,
                amount_usd=amount_usd,
                description=description,
                reason="DODO_API_KEY not configured",
            )

        amount_cents = int(round(amount_usd * 100))
        clean_cust_id = customer_ref.strip().replace(" ", "_")
        product_id = os.environ.get("DODO_PRODUCT_ID", f"prod_{clean_cust_id.lower()}")

        # Attempt 1: Checkout Sessions API (modern Dodo Payments endpoint)
        checkout_payload = {
            "customer": {
                "name": customer_ref,
                "email": f"{clean_cust_id.lower()}@example.com",
            },
            "product_cart": [
                {
                    "product_id": product_id,
                    "quantity": 1,
                    "amount": amount_cents,
                }
            ],
            "metadata": {
                "customer_ref": customer_ref,
                "description": description,
                "amount_usd": str(amount_usd),
                "source": "reconFX",
            },
        }

        try:
            url = f"{base_url}/checkouts"
            data = _http_post_json(url, checkout_payload, api_key)
            link = data.get("checkout_url") or data.get("payment_link")
            pid = data.get("session_id") or data.get("payment_id") or f"sess_{clean_cust_id.lower()}_{int(amount_usd)}"
            if link:
                logger.info("Successfully created Dodo Payments checkout session %s: %s", pid, link)
                return {
                    "payment_id": pid,
                    "payment_link": link,
                    "checkout_url": link,
                    "customer_ref": customer_ref,
                    "amount_usd": float(amount_usd),
                    "currency": "USD",
                    "description": description,
                    "status": "created",
                    "stub": False,
                    "dodo_reference": pid,
                    "raw_response": data,
                }
        except Exception as exc:
            logger.debug("Dodo /checkouts endpoint attempt failed: %s", exc)

        # Attempt 2: One-time Payments API
        payments_payload = {
            "billing": {"country": "US"},
            "customer": {
                "name": customer_ref,
                "email": f"{clean_cust_id.lower()}@example.com",
            },
            "payment_link": True,
            "product_cart": [
                {
                    "product_id": product_id,
                    "quantity": 1,
                    "amount": amount_cents,
                }
            ],
            "metadata": {
                "customer_ref": customer_ref,
                "description": description,
                "amount_usd": str(amount_usd),
                "source": "reconFX",
            },
        }

        try:
            url = f"{base_url}/payments"
            data = _http_post_json(url, payments_payload, api_key)
            link = data.get("payment_link") or data.get("checkout_url")
            pid = data.get("payment_id") or data.get("session_id") or f"pay_{clean_cust_id.lower()}_{int(amount_usd)}"
            if link:
                logger.info("Successfully created Dodo Payments payment %s: %s", pid, link)
                return {
                    "payment_id": pid,
                    "payment_link": link,
                    "checkout_url": link,
                    "customer_ref": customer_ref,
                    "amount_usd": float(amount_usd),
                    "currency": "USD",
                    "description": description,
                    "status": "created",
                    "stub": False,
                    "dodo_reference": pid,
                    "raw_response": data,
                }
        except Exception as exc:
            logger.warning("Dodo Payments API request failed (%s). Falling back to stub payment link.", exc)

        return _make_stub_collection(
            customer_ref=customer_ref,
            amount_usd=amount_usd,
            description=description,
            reason="Dodo Payments API request failed or returned no link",
        )
    except Exception as exc:
        logger.warning("Unexpected error in Dodo create_collection: %s", exc)
        return _make_stub_collection(
            customer_ref=customer_ref,
            amount_usd=amount_usd,
            description=description,
            reason=f"Unexpected error: {exc}",
        )



# Alias for README.md §6.3 compatibility
create_payment_link = create_collection
