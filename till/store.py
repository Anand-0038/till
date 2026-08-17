from __future__ import annotations

from till.domain import ShopNight
from till.fixtures import tuesday_night

_night: ShopNight | None = None


def reset() -> ShopNight:
    global _night
    _night = tuesday_night()
    return _night


def night() -> ShopNight:
    if _night is None:
        return reset()
    return _night
