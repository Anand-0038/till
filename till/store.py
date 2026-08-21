from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from till.domain import ShopNight
from till.fixtures import scenario_night, tuesday_night

_night: ShopNight | None = None


def reset(payload: Mapping[str, Any] | None = None) -> ShopNight:
    global _night
    _night = scenario_night(payload) if payload is not None else tuesday_night()
    return _night


def night() -> ShopNight:
    if _night is None:
        return reset()
    return _night
