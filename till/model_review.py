"""Optional model-backed Strands review for an already-observed close.

The model performs one bounded owner-review task: it reads the current synthetic
close through a read-only tool and summarizes which exceptions need attention.
The deterministic policy remains the only authority for actions, thresholds,
cash arithmetic, and packet filing.
"""

from __future__ import annotations

import os
from typing import Any

import openai
from strands import Agent, tool
from strands.models.openai import OpenAIModel
from strands.types.exceptions import (
    ContextWindowOverflowException,
    EventLoopException,
    ModelThrottledException,
    ProviderTokenCountError,
)

from till import tools
from till.store import night

FALLBACK_MESSAGE = "MODEL REVIEW UNAVAILABLE   provider failed; deterministic policy fallback remains active"


def _api_key() -> str:
    return os.environ.get("TILL_GEMINI_API_KEY", "").strip()


def _model_id() -> str:
    return (
        os.environ.get("TILL_GEMINI_MODEL", "gemini-2.5-flash").strip()
        or "gemini-2.5-flash"
    )


def enabled() -> bool:
    """Return whether the optional model-backed Strands review is configured."""

    return bool(_api_key())


@tool
def read_close_state() -> dict[str, Any]:
    """Read the bounded, synthetic close facts needed for owner review."""

    shop = night()
    tools.record_model_tool_call()
    return {
        "boundary": "local synthetic register fixture; no live POS or money movement",
        "shop": shop.shop,
        "date": shop.date,
        "sales_count": shop.sales_count,
        "expected_cash": str(shop.expected_cash),
        "counted_cash": str(shop.counted_cash)
        if shop.counted_cash is not None
        else None,
        "variance": str(shop.variance) if shop.variance is not None else None,
        "exceptions": [
            {
                "id": item.id,
                "kind": item.kind,
                "amount": str(item.amount),
                "reason": item.reason,
                "lane": item.lane,
                "status": item.status,
            }
            for item in shop.exceptions
            if item.lane == "ask"
        ],
    }


def _agent() -> Agent:
    key = _api_key()
    if not key:
        raise RuntimeError("optional Strands model review is not configured")

    model = OpenAIModel(
        model_id=_model_id(),
        client_args={
            "api_key": key,
            "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
            "timeout": 20.0,
            "max_retries": 1,
        },
        params={"temperature": 0.1, "max_tokens": 240},
        stream=False,
    )
    return Agent(
        model=model,
        tools=[read_close_state],
        system_prompt=(
            "You are Till's bounded owner-review agent. Call read_close_state exactly once. "
            "In two short sentences, summarize the observed exceptions that need the owner's "
            "attention and why. Do not calculate cash, invent transactions, choose approve or "
            "deny, alter policy, or claim any external action. The deterministic policy and "
            "owner gate remain authoritative. Mention that this is a local synthetic fixture."
        ),
        callback_handler=None,
        agent_id="till-owner-review",
        name="Till owner review",
    )


def run_model_review() -> str | None:
    """Run the real Strands model/tool loop when configured.

    Provider errors are returned as an explicit fallback tape message. The core
    close must remain usable when the optional provider is unavailable.
    """

    if not enabled():
        return None
    try:
        result = _agent()("Review the current register close for the owner.")
    except (
        ContextWindowOverflowException,
        EventLoopException,
        ModelThrottledException,
        OSError,
        openai.OpenAIError,
        ProviderTokenCountError,
        RuntimeError,
        TimeoutError,
        TypeError,
        ValueError,
    ):
        return FALLBACK_MESSAGE
    text = " ".join(str(result).split()).strip()
    if not text:
        return FALLBACK_MESSAGE
    return text[:1000]
