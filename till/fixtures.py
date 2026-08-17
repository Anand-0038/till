from till.domain import ExceptionItem, ShopNight, Tender, money
from till.policy import classify_exception


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
        variance=None,
        tenders=[
            Tender(method="cash", amount=expected, txn_count=18),
            Tender(method="card", amount=money(3180.20), txn_count=27),
            Tender(method="store-credit", amount=money(95.00), txn_count=2),
        ],
        exceptions=exceptions,
        status="open",
    )
