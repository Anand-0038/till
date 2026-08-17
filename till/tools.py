from __future__ import annotations

from typing import Any

from till.domain import Packet, TapeLine, money
from till.store import night


def _tape(agent: str, text: str, *, tool: str) -> None:
    night().tape.append(TapeLine(agent=agent, text=text, tool=tool))


def count_drawer() -> dict[str, Any]:
    shop = night()
    shop.counted_cash = money(1228.00)
    shop.variance = money(shop.counted_cash - shop.expected_cash)
    shop.status = "counting"
    _tape(
        "cashier",
        f"COUNT  expected {shop.expected_cash:.2f}  counted {shop.counted_cash:.2f}  var {shop.variance:.2f}",
        tool="count_drawer",
    )
    return {
        "expected_cash": shop.expected_cash,
        "counted_cash": shop.counted_cash,
        "variance": shop.variance,
    }


def classify_tenders() -> dict[str, Any]:
    shop = night()
    rows = [t.to_dict() for t in shop.tenders]
    _tape(
        "cashier",
        f"TAPE   {shop.sales_count} sales  cash {shop.expected_cash:.2f}  card {rows[1]['amount']:.2f}",
        tool="classify_tenders",
    )
    return {"sales_count": shop.sales_count, "tenders": rows}


def audit_exceptions() -> dict[str, Any]:
    shop = night()
    auto: list[dict[str, Any]] = []
    ask: list[dict[str, Any]] = []
    for item in shop.exceptions:
        if item.lane == "auto":
            item.status = "auto"
            auto.append(item.to_dict())
            _tape(
                "auditor",
                f"AUTO   {item.id}  {item.kind}  {item.amount:.2f}",
                tool="audit_exceptions",
            )
        else:
            item.status = "open"
            ask.append(item.to_dict())
            _tape(
                "auditor",
                f"ASK    {item.id}  {item.kind}  {item.amount:.2f}  {item.reason}",
                tool="audit_exceptions",
            )
    shop.status = "waiting" if ask else "counting"
    return {"auto": auto, "ask": ask}


ALLOWED_ACTIONS: dict[str, set[str]] = {
    "variance": {"accept"},
    "refund": {"approve", "deny"},
    "void": {"accept", "reverse"},
}


def _validated_decisions(decisions: list[dict[str, str]]) -> list[tuple[Any, str]]:
    shop = night()
    open_items = shop.open_asks()
    open_by_id = {item.id: item for item in open_items}
    seen: set[str] = set()
    normalized: list[tuple[Any, str]] = []

    if not isinstance(decisions, list) or not decisions:
        if not isinstance(decisions, list):
            raise TypeError("owner decisions must be a list")
        raise ValueError("at least one owner decision is required")

    for row in decisions:
        if not isinstance(row, dict):
            raise TypeError("owner decisions must be objects")
        card_id = row.get("id")
        action = row.get("action")
        if not isinstance(card_id, str) or not card_id.strip():
            raise ValueError("decision id must be a non-empty string")
        if not isinstance(action, str) or not action.strip():
            raise ValueError("decision action must be a non-empty string")
        card_id = card_id.strip()
        action = action.strip().lower()
        if card_id in seen:
            raise ValueError(f"duplicate decision for {card_id}")
        seen.add(card_id)

        item = open_by_id.get(card_id)
        if item is None:
            if card_id in {candidate.id for candidate in shop.exceptions}:
                raise ValueError(f"{card_id} is not an open ask card")
            raise ValueError(f"unknown card {card_id}")
        allowed = ALLOWED_ACTIONS.get(item.kind, set())
        if action not in allowed:
            choices = ", ".join(sorted(allowed)) or "no supported actions"
            raise ValueError(f"{item.id} accepts {choices}; received {action}")
        normalized.append((item, action))

    missing = sorted(set(open_by_id) - seen)
    if missing:
        raise ValueError(
            f"decide every open ask before filing; missing {', '.join(missing)}"
        )
    return normalized


def apply_decisions(decisions: list[dict[str, str]]) -> dict[str, Any]:
    shop = night()
    validated = _validated_decisions(decisions)
    applied: list[dict[str, str]] = []
    for item, action in validated:
        item.status = "decided"
        item.decision = action
        applied.append({"id": item.id, "action": action})
        _tape("owner", f"DECIDE {item.id}  {action}", tool="apply_decisions")
    return {"applied": applied, "open_asks": [e.to_dict() for e in shop.open_asks()]}


def file_deposit() -> dict[str, Any]:
    shop = night()
    if shop.open_asks():
        raise RuntimeError("cannot file deposit while ask cards are open")
    if shop.counted_cash is None:
        raise RuntimeError("cannot file deposit before the drawer is counted")
    packet_id = f"DEP-{shop.date}"
    decision_rows = [
        {"id": item.id, "action": item.decision or item.status}
        for item in shop.exceptions
        if item.lane == "ask"
    ]
    lines = [
        f"{shop.shop}  {shop.date}  {shop.register}",
        f"cash drop  {shop.counted_cash:.2f}",
        f"variance   {shop.variance:.2f}  {next(i.decision for i in shop.exceptions if i.id == 'VAR-TILL')}",
        f"refunds    REF-4412 {next(i.decision for i in shop.exceptions if i.id == 'REF-4412')}",
        "voids      VOID-19 auto (manager code)",
        "notes      NS-7 no-sale after 21:00",
    ]
    shop.packet = Packet(
        id=packet_id,
        cash_to_drop=shop.counted_cash,
        lines=lines,
        decisions=decision_rows,
    )
    shop.status = "locked"
    _tape(
        "clerk",
        f"FILE   {packet_id}  drop {shop.counted_cash:.2f}  LOCKED",
        tool="file_deposit",
    )
    return shop.packet.to_dict()
