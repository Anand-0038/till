from __future__ import annotations

from typing import Any

from till.domain import ExceptionItem, Packet, TapeLine, money
from till.policy import NO_SALE_NOTE_AFTER, minutes_from_hhmm
from till.store import night


def _tape(agent: str, text: str, *, tool: str) -> None:
    night().tape.append(TapeLine(agent=agent, text=text, tool=tool))


def record_model_tool_call() -> None:
    """Record the read-only tool call made by the optional Strands reviewer."""

    _tape(
        "auditor",
        "MODEL TOOL   read_close_state  read-only observed facts",
        tool="read_close_state",
    )


def record_model_review(text: str, *, fallback: bool = False) -> None:
    """Record a bounded model explanation without making it policy state."""

    _tape(
        "auditor",
        text[:1000],
        tool="model_review_fallback" if fallback else "model_review",
    )


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
    summary = "  ".join(f"{row['method']} {float(row['amount']):.2f}" for row in rows)
    _tape(
        "cashier",
        f"TAPE   {shop.sales_count} sales  {summary}",
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


def _decision_note(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError("decision note must be a string")
    note = " ".join(value.split())
    if len(note) > 240:
        raise ValueError("decision note must be 240 characters or fewer")
    return note or None


def _validated_decisions(
    decisions: list[dict[str, str]],
) -> list[tuple[Any, str, str | None]]:
    shop = night()
    open_items = shop.open_asks()
    open_by_id = {item.id: item for item in open_items}
    seen: set[str] = set()
    normalized: list[tuple[Any, str, str | None]] = []

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
        note = _decision_note(row.get("note"))
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
        normalized.append((item, action, note))

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
    for item, action, note in validated:
        item.status = "decided"
        item.decision = action
        item.decision_note = note
        applied_row = {"id": item.id, "action": action}
        if note:
            applied_row["note"] = note
        applied.append(applied_row)
        detail = f"DECIDE {item.id}  {action}"
        if note:
            detail += f"  note: {note}"
        _tape("owner", detail, tool="apply_decisions")
    return {"applied": applied, "open_asks": [e.to_dict() for e in shop.open_asks()]}


def file_deposit() -> dict[str, Any]:
    shop = night()
    if shop.packet is not None or shop.status == "locked":
        raise RuntimeError("deposit already filed")
    if shop.counted_cash is None:
        raise RuntimeError("cannot file deposit before the drawer is counted")
    if any(item.status == "pending" for item in shop.exceptions):
        raise RuntimeError("cannot file deposit before the auditor completes")
    unresolved_asks = [
        item
        for item in shop.exceptions
        if item.lane == "ask" and item.status != "decided"
    ]
    if unresolved_asks:
        raise RuntimeError("cannot file deposit while ask cards are unresolved")
    packet_id = f"DEP-{shop.date}"
    decision_rows = [
        {
            "id": item.id,
            "action": item.decision or item.status,
            **({"note": item.decision_note} if item.decision_note else {}),
        }
        for item in shop.exceptions
        if item.lane == "ask"
    ]
    lines = [
        f"{shop.shop}  {shop.date}  {shop.register}",
        f"cash drop  {shop.counted_cash:.2f}",
    ]
    lines.extend(_packet_line(item) for item in shop.exceptions)
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


def _packet_line(item: ExceptionItem) -> str:
    resolution = item.decision or item.status
    if item.kind == "variance":
        return f"variance   {item.amount:.2f}  {resolution}"
    if item.kind == "refund":
        return f"refunds    {item.id} {resolution}"
    if item.kind == "void":
        manager_note = " (manager code)" if item.manager_code else ""
        return f"voids      {item.id} {resolution}{manager_note}"
    if item.kind == "no-sale":
        threshold = f"{NO_SALE_NOTE_AFTER // 60:02d}:{NO_SALE_NOTE_AFTER % 60:02d}"
        if item.time_hhmm and minutes_from_hhmm(item.time_hhmm) >= NO_SALE_NOTE_AFTER:
            return f"notes      {item.id} no-sale after {threshold}"
        when = f" at {item.time_hhmm}" if item.time_hhmm else ""
        return f"notes      {item.id} no-sale{when}"
    return f"notes      {item.id} {item.reason} ({resolution})"
