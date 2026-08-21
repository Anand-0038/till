from __future__ import annotations

from typing import Any

from strands.hooks import BeforeNodeCallEvent, HookProvider, HookRegistry

from till.nodes import load_skill
from till.store import night
from till.tools import apply_decisions


def _as_decisions(response: Any) -> list[dict[str, Any]]:
    if isinstance(response, dict) and "decisions" in response:
        response = response["decisions"]
    if not isinstance(response, list):
        raise TypeError("owner gate expects a list of {id, action}")

    decisions: list[dict[str, Any]] = []
    for row in response:
        if not isinstance(row, dict):
            raise TypeError("owner gate decisions must be objects")
        card_id = row.get("id")
        action = row.get("action")
        if not isinstance(card_id, str) or not card_id.strip():
            raise ValueError("owner gate decision id must be a non-empty string")
        if not isinstance(action, str) or not action.strip():
            raise ValueError("owner gate decision action must be a non-empty string")
        note = row.get("note")
        if note is not None and not isinstance(note, str):
            raise TypeError("owner gate decision note must be a string")
        decisions.append(
            {
                "id": card_id.strip(),
                "action": action.strip().lower(),
                **({"note": note} if note is not None else {}),
            }
        )
    return decisions


class OwnerGate(HookProvider):
    def register_hooks(self, registry: HookRegistry, **kwargs) -> None:
        registry.add_callback(BeforeNodeCallEvent, self.gate)

    def gate(self, event: BeforeNodeCallEvent) -> None:
        if event.node_id != "clerk":
            return
        role_contract = load_skill("owner-gate").splitlines()[1]
        while night().open_asks():
            cards = [item.to_dict() for item in night().open_asks()]
            response = event.interrupt(
                "owner-gate", reason={"role": role_contract, "cards": cards}
            )
            apply_decisions(_as_decisions(response))
