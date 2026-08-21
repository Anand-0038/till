"""Optional model-generated explanation for an already-computed close.

The close policy never calls this module. Gemini receives a bounded, synthetic
summary of the observed night and can only produce explanatory text. It cannot
count the drawer, choose an owner action, or file the packet.
"""

from __future__ import annotations

import json
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen


class NarrationUnavailable(RuntimeError):
    """Raised when optional Gemini narration is not configured."""


class NarrationProviderError(RuntimeError):
    """Raised when the optional Gemini request cannot produce an explanation."""


def _api_key() -> str:
    return os.environ.get("TILL_GEMINI_API_KEY", "").strip()


def _model() -> str:
    return (
        os.environ.get("TILL_GEMINI_MODEL", "gemini-2.5-flash").strip()
        or "gemini-2.5-flash"
    )


def _bounded_context(night: dict[str, Any]) -> dict[str, Any]:
    """Keep the model input limited to synthetic, already-observed close facts."""

    drawer = night.get("drawer") or {}
    packet = night.get("packet") or {}
    return {
        "boundary": "local synthetic fixture; no live POS or money movement",
        "shop": night.get("shop"),
        "date": night.get("date"),
        "status": night.get("status"),
        "sales": night.get("sales"),
        "drawer": {
            "expected": drawer.get("expected"),
            "counted": drawer.get("counted"),
            "variance": drawer.get("variance"),
        },
        "tape": [
            {
                "agent": line.get("agent"),
                "tool": line.get("tool"),
                "text": line.get("text"),
            }
            for line in (night.get("tape") or [])
        ],
        "open_asks": [
            {
                "id": card.get("id"),
                "kind": card.get("kind"),
                "amount": card.get("amount"),
                "reason": card.get("reason"),
                "status": card.get("status"),
            }
            for card in (night.get("open_asks") or [])
        ],
        "packet": {
            "id": packet.get("id"),
            "cash_to_drop": packet.get("cash_to_drop"),
            "decisions": packet.get("decisions") or [],
        }
        if packet
        else None,
    }


def build_prompt(night: dict[str, Any]) -> str:
    context = json.dumps(_bounded_context(night), sort_keys=True, ensure_ascii=True)
    return (
        "You are an optional operations narrator for Till, a local synthetic "
        "night-register workflow. Explain only what the observed trace proves. "
        "In 2 or 3 short sentences, state what the crew completed, what the "
        "owner still needs to decide (if anything), and the next safe state. "
        "Never invent transactions, customers, policy decisions, or external "
        "system effects. Say that the data is a local synthetic fixture when "
        "relevant. The deterministic policy, owner gate, and packet state are "
        "authoritative; you are only explaining them.\n\n"
        f"Observed close context:\n{context}"
    )


def _text_from_response(payload: dict[str, Any]) -> str:
    candidates = payload.get("candidates") or []
    if not candidates:
        raise NarrationProviderError("Gemini returned no explanation candidate")
    parts = (candidates[0].get("content") or {}).get("parts") or []
    text = " ".join(
        part.get("text", "").strip()
        for part in parts
        if isinstance(part, dict) and isinstance(part.get("text"), str)
    ).strip()
    if not text:
        raise NarrationProviderError("Gemini returned no explanation text")
    return " ".join(text.split())[:1200]


def generate_narration(night: dict[str, Any]) -> dict[str, str]:
    key = _api_key()
    if not key:
        raise NarrationUnavailable("optional Gemini narration is not configured")

    model = _model()
    endpoint = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{quote(model, safe='.-_')}"
        ":generateContent?"
        f"{urlencode({'key': key})}"
    )
    body = json.dumps(
        {
            "contents": [{"role": "user", "parts": [{"text": build_prompt(night)}]}],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 240,
            },
        }
    ).encode("utf-8")
    request = Request(
        endpoint,
        data=body,
        method="POST",
        headers={"Accept": "application/json", "Content-Type": "application/json"},
    )
    try:
        with urlopen(request, timeout=25) as response:
            payload = json.load(response)
    except HTTPError as exc:
        raise NarrationProviderError(
            f"Gemini request failed with HTTP {exc.code}"
        ) from exc
    except (URLError, TimeoutError) as exc:
        raise NarrationProviderError(
            "Gemini request could not reach the provider"
        ) from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise NarrationProviderError("Gemini returned an unreadable response") from exc

    return {
        "provider": "gemini",
        "model": model,
        "narration": _text_from_response(payload),
        "boundary": "optional-model-explanation; policy remains deterministic",
    }
