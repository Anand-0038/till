from collections.abc import Mapping
from typing import Any

from till.domain import ExceptionItem, ShopNight, Tender, money
from till.policy import classify_exception


def scenario_night(payload: Mapping[str, Any]) -> ShopNight:
    """Build a validated, policy-ready night from a POS-neutral close packet."""

    required = (
        "shop",
        "owner",
        "date",
        "register",
        "sales_count",
        "expected_cash",
        "counted_cash",
        "tenders",
        "exceptions",
    )
    missing = [key for key in required if key not in payload]
    if missing:
        raise ValueError(f"close packet missing {', '.join(missing)}")

    expected = money(payload["expected_cash"])
    counted = money(payload["counted_cash"])
    variance = money(counted - expected)
    variance_id = str(payload.get("variance_id") or "VAR-CLOSE").strip()
    if not variance_id:
        raise ValueError("variance_id must be non-empty")

    exceptions: list[ExceptionItem] = [
        ExceptionItem(
            id=variance_id,
            kind="variance",
            amount=variance,
            reason="Drawer short or over against the POS cash total",
            lane=classify_exception("variance", variance),
        )
    ]
    seen_ids = {variance_id}
    for raw in payload["exceptions"]:
        if not isinstance(raw, Mapping):
            raise TypeError("each exception must be an object")
        item_id = str(raw.get("id") or "").strip()
        kind = str(raw.get("kind") or "").strip()
        reason = str(raw.get("reason") or "").strip()
        if not item_id or not kind or not reason:
            raise ValueError("each exception needs id, kind, and reason")
        if item_id in seen_ids:
            raise ValueError(f"duplicate exception id {item_id}")
        if kind == "variance":
            raise ValueError("variance is derived from expected_cash and counted_cash")
        if kind not in {"refund", "void", "no-sale"}:
            raise ValueError(f"unsupported exception kind: {kind}")
        amount = money(raw.get("amount", 0))
        manager_code = bool(raw.get("manager_code", False))
        receipt = bool(raw.get("receipt", False))
        time_hhmm = raw.get("time_hhmm")
        if time_hhmm is not None:
            time_hhmm = str(time_hhmm).strip()
        exceptions.append(
            ExceptionItem(
                id=item_id,
                kind=kind,
                amount=amount,
                reason=reason,
                lane=classify_exception(
                    kind,
                    amount,
                    manager_code=manager_code,
                    time_hhmm=time_hhmm,
                    receipt=receipt,
                ),
                manager_code=manager_code,
                time_hhmm=time_hhmm,
                receipt=receipt,
            )
        )
        seen_ids.add(item_id)

    tenders = [
        Tender(
            method=str(raw["method"]).strip(),
            amount=money(raw["amount"]),
            txn_count=int(raw["txn_count"]),
        )
        for raw in payload["tenders"]
    ]
    return ShopNight(
        shop=str(payload["shop"]).strip(),
        owner=str(payload["owner"]).strip(),
        date=str(payload["date"]).strip(),
        register=str(payload["register"]).strip(),
        sales_count=int(payload["sales_count"]),
        expected_cash=expected,
        counted_cash=None,
        counted_cash_input=counted,
        variance=None,
        tenders=tenders,
        exceptions=exceptions,
        status="open",
    )


def tuesday_night() -> ShopNight:
    expected = money(1240.50)
    counted = money(1228.00)
    variance = money(counted - expected)
    exceptions = [
        ExceptionItem(
            id="VAR-TILL",
            kind="variance",
            amount=variance,
            reason="Drawer short against POS cash total",
            lane=classify_exception("variance", variance),
        ),
        ExceptionItem(
            id="REF-4412",
            kind="refund",
            amount=money(89.00),
            reason="Circular saw blade set returned with receipt",
            lane=classify_exception("refund", 89.00, receipt=True),
            receipt=True,
        ),
        ExceptionItem(
            id="VOID-19",
            kind="void",
            amount=money(24.00),
            reason="Double ring on fasteners, voided with manager code",
            lane=classify_exception("void", 24.00, manager_code=True),
            manager_code=True,
        ),
        ExceptionItem(
            id="NS-7",
            kind="no-sale",
            amount=money(0),
            reason="No-sale at 21:14 for parking change",
            lane=classify_exception("no-sale", 0, time_hhmm="21:14"),
            time_hhmm="21:14",
        ),
    ]
    return ShopNight(
        shop="Oak & Bit Hardware",
        owner="Dana Reyes",
        date="2026-08-11",
        register="REG-1",
        sales_count=47,
        expected_cash=expected,
        counted_cash=None,
        counted_cash_input=counted,
        variance=None,
        tenders=[
            Tender(method="cash", amount=expected, txn_count=18),
            Tender(method="card", amount=money(3180.20), txn_count=27),
            Tender(method="store-credit", amount=money(95.00), txn_count=2),
        ],
        exceptions=exceptions,
        status="open",
    )
