"""Single source of truth for auto vs ask."""

VARIANCE_CAP = 10.00
REFUND_CAP = 50.00
NO_SALE_NOTE_AFTER = 21 * 60

POLICY_TABLE = [
    {"event": "Tender totals match POS", "auto": "file", "ask": "—"},
    {"event": f"Drawer variance ≤ ${VARIANCE_CAP:g}", "auto": "accept as variance", "ask": "—"},
    {"event": f"Drawer variance > ${VARIANCE_CAP:g}", "auto": "—", "ask": "accept"},
    {"event": f"Refund ≤ ${REFUND_CAP:g} with receipt", "auto": "post", "ask": "—"},
    {"event": f"Refund > ${REFUND_CAP:g}", "auto": "—", "ask": "approve / deny"},
    {"event": "Void with manager code", "auto": "accept", "ask": "—"},
    {"event": "Void without manager code", "auto": "—", "ask": "accept / reverse"},
    {"event": "No-sale after 21:00", "auto": "note on packet", "ask": "—"},
]


def minutes_from_hhmm(hhmm: str) -> int:
    hour, minute = hhmm.split(":")
    return int(hour) * 60 + int(minute)


def classify_exception(
    kind: str,
    amount: float,
    *,
    manager_code: bool = False,
    time_hhmm: str | None = None,
    receipt: bool = False,
) -> str:
    if kind == "variance":
        return "auto" if abs(amount) <= VARIANCE_CAP else "ask"
    if kind == "refund":
        return "auto" if amount <= REFUND_CAP and receipt else "ask"
    if kind == "void":
        return "auto" if manager_code else "ask"
    if kind == "no-sale":
        if time_hhmm and minutes_from_hhmm(time_hhmm) >= NO_SALE_NOTE_AFTER:
            return "auto"
        return "auto"
    raise ValueError(f"unknown exception kind: {kind}")
