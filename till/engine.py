from __future__ import annotations

from threading import RLock
from typing import Any

from strands.multiagent.base import Status

from till.graph import build_graph
from till.store import night, reset

_graph = None
_last_result = None
_ENGINE_LOCK = RLock()


def snapshot() -> dict[str, Any]:
    with _ENGINE_LOCK:
        return night().to_dict()


def _payload(result) -> dict[str, Any]:
    shop = snapshot()
    if result.status == Status.INTERRUPTED:
        shop["run"] = {
            "status": "interrupted",
            "interrupts": [
                {"id": item.id, "name": item.name, "reason": item.reason}
                for item in result.interrupts
            ],
        }
        return shop
    status = (
        result.status.value if hasattr(result.status, "value") else str(result.status)
    )
    shop["run"] = {"status": status}
    return shop


def start_close() -> dict[str, Any]:
    global _graph, _last_result
    with _ENGINE_LOCK:
        reset()
        _graph = None
        _last_result = None
        try:
            _graph = build_graph()
            _last_result = _graph("Close the Tuesday night at Oak & Bit Hardware.")
        except Exception:
            # Do not leave a failed graph pointing at partially mutated fixture state.
            _graph = None
            _last_result = None
            reset()
            raise
        return _payload(_last_result)


def resume_close(decisions: list[dict[str, str]]) -> dict[str, Any]:
    global _last_result
    with _ENGINE_LOCK:
        if _graph is None or _last_result is None:
            raise RuntimeError("no close in progress")
        if _last_result.status != Status.INTERRUPTED:
            raise RuntimeError("night is not waiting on the owner")
        responses = [
            {"interruptResponse": {"interruptId": item.id, "response": decisions}}
            for item in _last_result.interrupts
        ]
        _last_result = _graph(responses)
        return _payload(_last_result)


def export_close() -> dict[str, Any]:
    with _ENGINE_LOCK:
        if _last_result is None:
            raise RuntimeError("no close in progress")
        if (
            _last_result.status != Status.COMPLETED
            or night().status != "locked"
            or night().packet is None
        ):
            raise RuntimeError("export is available after the deposit packet is locked")
        return {
            "format": "till-close-v1",
            "boundary": "local-process",
            "night": _payload(_last_result),
        }


def reset_night() -> dict[str, Any]:
    global _graph, _last_result
    with _ENGINE_LOCK:
        _graph = None
        _last_result = None
        reset()
        return snapshot()
